#!/usr/bin/env python3
"""
Regenerates the cropped renders, RGB multi-zone masks (Primary=R, Secondary=G, Accent=B),
and Base64 data bundle (renders-data.js) for the VAULT Color Studio.

Configuration:
  Reads VAULT_USSA_DIR from environment variable or local .env file.
  If raw extracted images in ./assets/ are missing, extracts them automatically
  from VAULT_USSA_DIR using `pdfimages` and copies the high-res Naming PNGs.
"""
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np
import os, sys, shutil, subprocess, base64, io, json

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / 'assets'
RENDERS_DIR = ROOT_DIR / 'renders'


def load_dotenv(dotenv_path: Path):
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def ensure_assets(vault_dir: Path):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        ASSETS_DIR / 'drawers-exploded.png',
        ASSETS_DIR / 'sustainers-exploded.png',
        ASSETS_DIR / 'manual-003.png',
        ASSETS_DIR / 'manual-007.png',
        ASSETS_DIR / 'drawer-step-001.png',
        ASSETS_DIR / 'drawer-step-007.png',
    ]
    if not all(p.exists() for p in required):
        if not vault_dir or not vault_dir.exists():
            sys.exit(
                f"Error: Missing raw assets in {ASSETS_DIR} and VAULT_USSA_DIR ({vault_dir}) does not exist.\n"
                f"Set VAULT_USSA_DIR in .env or environment to point to your USSA VAULT archive."
            )

        print(f"Extracting source renders from VAULT_USSA_DIR: {vault_dir}")
        shutil.copy2(vault_dir / '01. DRAWERS' / 'Drawers Naming.png', ASSETS_DIR / 'drawers-exploded.png')
        shutil.copy2(vault_dir / '02. SUSTAINERS' / 'Sustainer Naming.png', ASSETS_DIR / 'sustainers-exploded.png')
        if (vault_dir / '03. MODIFICATIONS' / 'XL Mods Naming.png').exists():
            shutil.copy2(vault_dir / '03. MODIFICATIONS' / 'XL Mods Naming.png', ASSETS_DIR / 'mods-exploded.png')

        subprocess.run([
            'pdfimages', '-png', '-f', '2', '-l', '19',
            str(vault_dir / '01_Instructions Manual.pdf'),
            str(ASSETS_DIR / 'manual')
        ], check=True)

        subprocess.run([
            'pdfimages', '-png', '-f', '1', '-l', '8',
            str(vault_dir / '02_Drawer Assembly.pdf'),
            str(ASSETS_DIR / 'drawer-step')
        ], check=True)


def erode(mask_bool: np.ndarray, size: int = 3) -> np.ndarray:
    if size <= 1:
        return mask_bool
    img = Image.fromarray(mask_bool.astype(np.uint8) * 255)
    return np.array(img.filter(ImageFilter.MinFilter(size))) > 0


def dilate(mask_bool: np.ndarray, size: int = 3) -> np.ndarray:
    if size <= 1:
        return mask_bool
    img = Image.fromarray(mask_bool.astype(np.uint8) * 255)
    return np.array(img.filter(ImageFilter.MaxFilter(size))) > 0


def reconstruct(seed: np.ndarray, mask: np.ndarray, max_iter: int = 160) -> np.ndarray:
    """Morphological geodesic reconstruction by dilation: grows `seed` inside `mask`."""
    cur = seed & mask
    for _ in range(max_iter):
        nxt = dilate(cur, 3) & mask
        if np.array_equal(nxt, cur):
            break
        cur = nxt
    return cur


def close_holes(mask_bool: np.ndarray, size: int = 5) -> np.ndarray:
    """Morphological closing to bridge 1-2px callout lines or tiny specular gaps."""
    return erode(dilate(mask_bool, size), size)


def feather_masks(m_pri: np.ndarray, m_sec: np.ndarray, m_acc: np.ndarray, radius: float = 0.65):
    """Applies sub-pixel anti-aliasing to mask boundaries while keeping interior weights at 1.0."""
    def blur_ch(m):
        im = Image.fromarray((m.astype(np.uint8) * 255)).filter(ImageFilter.GaussianBlur(radius=radius))
        return np.array(im).astype(float) / 255.0

    fp = blur_ch(m_pri)
    fs = blur_ch(m_sec)
    fa = blur_ch(m_acc)
    tot = fp + fs + fa
    safe_tot = np.maximum(tot, 1.0)
    return fp / safe_tot, fs / safe_tot, fa / safe_tot


renders_bundle = {}


def save_render_and_mask(name, title, subtitle, img, m_pri_bool, m_sec_bool, m_acc_bool):
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    mask_r, mask_g, mask_b = feather_masks(m_pri_bool, m_sec_bool, m_acc_bool, radius=0.6)
    mr = Image.fromarray((np.clip(mask_r, 0, 1) * 255).astype(np.uint8))
    mg = Image.fromarray((np.clip(mask_g, 0, 1) * 255).astype(np.uint8))
    mb = Image.fromarray((np.clip(mask_b, 0, 1) * 255).astype(np.uint8))
    mask_img = Image.merge('RGB', (mr, mg, mb))
    img.save(RENDERS_DIR / f'{name}.png', optimize=True)
    mask_img.save(RENDERS_DIR / f'{name}-mask.png', optimize=True)

    buf_img = io.BytesIO()
    img.save(buf_img, format='WEBP', quality=91)
    b64_img = 'data:image/webp;base64,' + base64.b64encode(buf_img.getvalue()).decode('ascii')

    buf_mask = io.BytesIO()
    mask_img.save(buf_mask, format='WEBP', quality=94)
    b64_mask = 'data:image/webp;base64,' + base64.b64encode(buf_mask.getvalue()).decode('ascii')

    renders_bundle[name] = {
        'id': name,
        'title': title,
        'subtitle': subtitle,
        'width': img.size[0],
        'height': img.size[1],
        'src': b64_img,
        'mask': b64_mask
    }
    print(f'Saved {name} ({img.size[0]}x{img.size[1]})')


def process_grey_bg_exploded(src_path, out_name, title, subtitle, crop_box, out_size, sec_max_lum=92):
    img_full = Image.open(src_path).convert('RGB')
    w, h = img_full.size
    crop = img_full.crop((
        int(w * crop_box[0]), int(h * crop_box[1]),
        int(w * crop_box[2]), int(h * crop_box[3])
    )).resize(out_size, Image.Resampling.LANCZOS)
    arr = np.array(crop).astype(float)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = (r + g + b) / 3.0
    coolness = b - r

    # Background is flat [157, 163, 170]; black callout lines/text on background obey the same RGB ratio:
    bg_callout_err = np.abs(g - r * (163.0 / 157.0)) + np.abs(b - r * (170.0 / 157.0))
    is_bg_or_bg_text = (bg_callout_err < 3.2) & (r <= 158.5)
    is_fg = ~is_bg_or_bg_text

    # 1. Accent (orange hardware)
    raw_acc = is_fg & (r - b > 18) & (r > g)
    seed_acc = erode(raw_acc & (r - b > 28), 3)
    m_acc = reconstruct(seed_acc, is_fg & (r - b > 10))

    # 2. Secondary (dark grey 3D parts; MinFilter(5) seed strips all 1-2px callout lines & text)
    raw_sec = is_fg & (~m_acc) & (lum >= 24) & (lum <= sec_max_lum) & (coolness < 8.5)
    seed_sec = erode(raw_sec & (lum >= 32) & (lum <= sec_max_lum - 6), 5)
    m_sec = reconstruct(seed_sec, raw_sec)
    m_sec = close_holes(m_sec, 5) & is_fg & (~m_acc)

    # 3. Primary (light grey 3D parts)
    raw_pri = is_fg & (~m_acc) & (~m_sec) & (lum > 75) & (coolness < 9.0)
    seed_pri = erode(raw_pri & (lum > 115), 3)
    m_pri = reconstruct(seed_pri, raw_pri)
    m_pri = close_holes(m_pri, 5) & is_fg & (~m_acc) & (~m_sec)

    save_render_and_mask(out_name, title, subtitle, crop, m_pri, m_sec, m_acc)


def process_white_bg_render(src_path, out_name, title, subtitle, crop_box, out_size, mode='default'):
    img_full = Image.open(src_path).convert('RGB')
    w0, h0 = img_full.size
    crop = img_full.crop((
        int(w0 * crop_box[0]), int(h0 * crop_box[1]),
        int(w0 * crop_box[2]), int(h0 * crop_box[3])
    )).resize(out_size, Image.Resampling.LANCZOS)
    arr = np.array(crop).astype(float)
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yn, xn = yy / float(h), xx / float(w)

    if mode == 'both_types':
        # Remove top-right curved orange arrow & background labels ('1. drawers', '2. sustainers')
        top_arrow = (xn > 0.635) & (yn < 0.45) & (arr[:, :, 0] - arr[:, :, 2] > 12)
        labels_bg = ((xn < 0.28) & (yn < 0.56) & (yn < 0.60 - xn * 0.45)) | ((xn > 0.38) & (xn < 0.59) & (yn < 0.145))
        arr[top_arrow | labels_bg] = 255.0

        # Neutralize orange tutorial arrow inside the open dark drawer floor so it recolors with Secondary
        inner_box = (xn > 0.40) & (xn < 0.60) & (yn > 0.66) & (yn < 0.83)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        arrow_px = inner_box & (r - b > 12)
        neutral_val = np.clip(64.0 + (g - 102.0) * 0.35, 35.0, 78.0)
        for c in range(3):
            arr[:, :, c] = np.where(arrow_px, neutral_val, arr[:, :, c])

    elif mode == 'latch_stoppers':
        # Remove (11), (12), horizontal dashed line, and 'result' arrows sitting on white background
        clutter = (
            ((xn < 0.10) & (yn < 0.14)) |
            ((xn < 0.10) & (yn > 0.58) & (yn < 0.68)) |
            ((yn > 0.405) & (yn < 0.435)) |
            ((xn > 0.415) & (xn < 0.595))
        )
        arr[clutter] = 255.0
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        blue_arrow = (b - r > 22) & (xn < 0.46)
        arr[blue_arrow & (yn < 0.40)] = 255.0
        for c in range(3):
            arr[:, :, c] = np.where(blue_arrow & (yn >= 0.40), 212.0, arr[:, :, c])

    crop_clean = Image.fromarray(arr.astype(np.uint8))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = (r + g + b) / 3.0
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)

    # Flood-fill exterior white background from image borders so bright interior surfaces never get holes
    border = np.zeros((h, w), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    bg_thresh = 223 if mode == 'both_types' else (225 if mode == 'interiors' else 230)
    is_bg = reconstruct(border, (lum > bg_thresh) & (sat < 15), max_iter=220)
    is_fg = ~is_bg

    # 1. Accent
    raw_acc = is_fg & (r - b > 24) & (r > g)
    m_acc = dilate(raw_acc, 3) & is_fg & (r - b > 12)

    # 2. Secondary
    dark_max = 104 if mode in ('both_types', 'interiors') else 112
    raw_sec = is_fg & (~m_acc) & (sat < 26) & (lum >= 18) & (lum <= dark_max)
    if mode == 'latch_stoppers':
        guide_lines = (xn > 0.19) & (xn < 0.30) & (yn > 0.52) & (yn < 0.72)
        raw_sec = raw_sec & (~guide_lines)
    seed_sec = erode(raw_sec & (lum <= dark_max - 10), 3 if mode == 'interiors' else 5)
    m_sec = reconstruct(seed_sec, raw_sec, max_iter=100)
    m_sec = close_holes(m_sec, 5) & is_fg & (~m_acc)

    # 3. Primary
    raw_pri = is_fg & (~m_acc) & (~m_sec) & (sat < 22) & (lum > 85) & (lum < 245)
    if mode == 'latch_stoppers':
        guide_lines_bg = (xn > 0.19) & (xn < 0.30) & (yn > 0.52) & (yn < 0.635)
        raw_pri = raw_pri & (~guide_lines_bg)
    seed_pri = erode(raw_pri & (lum > 120) & (lum < 222), 5)
    m_pri = reconstruct(seed_pri, raw_pri, max_iter=140)
    m_pri = close_holes(m_pri, 5) & is_fg & (~m_acc) & (~m_sec)

    save_render_and_mask(out_name, title, subtitle, crop_clean, m_pri, m_sec, m_acc)


def process_studio_stacks(web_dir: Path):
    s3_path = web_dir / 's3-studio.png'
    l3_path = web_dir / 'sustainer-L3-studio.png'
    if not (s3_path.exists() and l3_path.exists()):
        return

    s3 = Image.open(s3_path).convert('RGB')
    l3 = Image.open(l3_path).convert('RGB')
    w1, h1 = s3.size
    c_s3 = s3.crop((int(w1 * 0.32), int(h1 * 0.09), int(w1 * 0.72), int(h1 * 0.89))).resize((440, 660), Image.Resampling.LANCZOS)
    w2, h2 = l3.size
    c_l3 = l3.crop((int(w2 * 0.24), int(h2 * 0.05), int(w2 * 0.78), int(h2 * 0.90))).resize((520, 660), Image.Resampling.LANCZOS)

    comp = Image.new('RGB', (960, 660), (247, 247, 247))
    comp.paste(c_s3, (0, 0))
    comp.paste(c_l3, (440, 0))
    arr = np.array(comp).astype(float)
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yn, xn = yy / float(h), xx / float(w)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = arr.mean(axis=2)
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)

    # Trim below bottom contact edges to preserve glossy studio table reflection
    left_floor = np.where(xn < 0.195, 0.840 + ((xn - 0.065) / 0.130) * 0.068, 0.908 - ((xn - 0.195) / 0.220) * 0.055)
    right_floor = np.where(xn < 0.585, 0.870 + ((xn - 0.500) / 0.085) * 0.055, 0.925 - ((xn - 0.585) / 0.370) * 0.125)
    above_floor = np.where(
        xn < 0.458,
        (xn >= 0.068) & (xn <= 0.408) & (yn <= left_floor),
        (xn >= 0.500) & (yn <= right_floor)
    )

    border = np.zeros((h, w), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    is_bg = reconstruct(border, (lum > 235) & (sat < 12), max_iter=200) | (~above_floor)
    is_fg = ~is_bg

    # 1. Accent: 6 orange side stoppers on S3 stack
    raw_acc = is_fg & (r - b > 28) & (r > g)
    m_acc = dilate(raw_acc, 3) & is_fg & (r - b > 14)

    # 2. Secondary: lock gears on S3 + latches, labels, and M3 bolts on L3 (excluding horizontal stacking shadow seams)
    s3_seams = (xn < 0.458) & (((yn > 0.535) & (yn < 0.566)) | ((yn > 0.765) & (yn < 0.825)))
    l3_latches_x = ((xn > 0.682) & (xn < 0.760)) | ((xn > 0.865) & (xn < 0.930))
    l3_seams = (xn >= 0.458) & (~l3_latches_x) & (((yn > 0.518) & (yn < 0.552)) | ((yn > 0.730) & (yn < 0.795)))
    raw_sec = is_fg & (~m_acc) & (~s3_seams) & (~l3_seams) & (lum < 114)
    seed_sec = erode(raw_sec & (lum < 95), 3)
    m_sec = reconstruct(seed_sec, raw_sec, max_iter=80)
    m_sec = close_holes(m_sec, 5) & is_fg & (~m_acc)

    # 3. Primary: light grey shells & keys (including specular bevel highlights)
    m_pri = is_fg & (~m_acc) & (~m_sec)
    m_pri = close_holes(m_pri, 5) & is_fg & (~m_acc) & (~m_sec)

    save_render_and_mask(
        '07-studio-stacks',
        'Studio Stack: S3 Drawers & L3 Sustainers',
        'Callout-free studio render comparing a 3-high S3 Drawer stack (left) and 3-high L3 Sustainer stack (right)',
        comp, m_pri, m_sec, m_acc
    )


def process_studio_drawer_interior(web_dir: Path):
    p182 = web_dir / 'drawer-interior-182.png'
    if not p182.exists():
        return

    out_size = (960, 600)
    crop_box = (0.14, 0.0, 0.86, 0.98)
    im = Image.open(p182).convert('RGB')
    w0, h0 = im.size
    arr = np.array(im.crop((
        int(w0 * crop_box[0]), int(h0 * crop_box[1]),
        int(w0 * crop_box[2]), int(h0 * crop_box[3])
    )).resize(out_size, Image.Resampling.LANCZOS)).astype(float)
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yn, xn = yy / float(h), xx / float(w)
    lum = arr.mean(axis=2)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Perspective silhouette of the L4 Drawer
    left_bound = np.where(
        yn < 0.635,
        0.215 - (yn / 0.635) * 0.078,
        np.where(yn < 0.855, 0.165 - ((yn - 0.635) / 0.220) * 0.038, 0.088)
    )
    right_bound = np.where(
        yn < 0.635,
        0.785 + (yn / 0.635) * 0.078,
        np.where(yn < 0.855, 0.835 + ((yn - 0.635) / 0.220) * 0.038, 0.912)
    )
    bottom_bound = (yn < 0.920) | ((xn > 0.435) & (xn < 0.555) & (yn < 0.972))
    in_bounds = (xn >= left_bound) & (xn <= right_bound) & (yn >= 0.008) & bottom_bound

    interior_rect = (yn > 0.375) & (yn < 0.920) & (xn > left_bound + 0.012) & (xn < right_bound - 0.012)
    is_model = in_bounds & ((lum > 124) | interior_rect | ((xn > 0.435) & (xn < 0.555) & (yn > 0.88) & (lum > 75)))
    is_model = close_holes(is_model, 5) & in_bounds

    # 6 Gridfinity bins inside the dark drawer box cavity
    bin_left = 0.232 - ((yn - 0.398) / 0.457) * 0.042
    bin_right = 0.768 + ((yn - 0.398) / 0.457) * 0.042
    in_bin_zone = (yn >= 0.398) & (yn <= 0.855) & (xn >= bin_left) & (xn <= bin_right)
    bins_mask = in_bin_zone & (lum > 94)
    bins_mask = close_holes(bins_mask, 9) & in_bin_zone & (lum > 78)

    spring_mask = is_model & (r - b > 25) & (r > g)
    m_acc = bins_mask | dilate(spring_mask, 3)

    drawer_cavity = (yn >= 0.382) & (yn <= 0.856) & (xn >= left_bound + 0.024) & (xn <= right_bound - 0.024)
    dark_inner_box = drawer_cavity & (~m_acc) & (lum < 128)
    front_lock_label = is_model & (~drawer_cavity) & (~m_acc) & (yn > 0.55) & (lum < 105)
    m_sec = dark_inner_box | front_lock_label
    m_pri = is_model & (~m_acc) & (~m_sec) & (lum > 95)

    # Tint the 6 Gridfinity bins in the reference image to USSA Orange so original comparison matches all 3 zones
    arr_out = arr.copy()
    orange_rgb = np.array([238.0, 108.0, 32.0])
    for c in range(3):
        scaled = np.where(
            lum <= 185.0,
            orange_rgb[c] * (lum / 185.0) ** 0.95,
            orange_rgb[c] + (255.0 - orange_rgb[c]) * ((lum - 185.0) / 70.0) * 0.7
        )
        arr_out[:, :, c] = np.where(bins_mask, np.clip(scaled, 0, 255), arr_out[:, :, c])

    save_render_and_mask(
        '08-drawer-interior',
        'Open L4 Drawer & Gridfinity Bins (Studio)',
        'Studio close-up of open L4 Drawer showing Outer Shell & Key (Primary), Inner Box & Lock (Secondary), and 6 Gridfinity Bins & Spring (Accent)',
        Image.fromarray(arr_out.astype(np.uint8)), m_pri, m_sec, m_acc
    )


def process_studio_sustainer_interior(web_dir: Path):
    p184 = web_dir / 'sustainer-interior-184.png'
    p190 = web_dir / 'sustainer-interior-190.png'
    if not (p184.exists() and p190.exists()):
        return

    out_size = (960, 600)
    crop_box = (0.14, 0.0, 0.86, 0.96)
    def load_sust(p):
        im = Image.open(p).convert('RGB')
        w0, h0 = im.size
        return np.array(im.crop((
            int(w0 * crop_box[0]), int(h0 * crop_box[1]),
            int(w0 * crop_box[2]), int(h0 * crop_box[3])
        )).resize(out_size, Image.Resampling.LANCZOS)).astype(float)

    arr184 = load_sust(p184)
    arr190 = load_sust(p190)
    h, w, _ = arr190.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yn, xn = yy / float(h), xx / float(w)
    lum184 = arr184.mean(axis=2)
    lum190 = arr190.mean(axis=2)
    r, g, b = arr190[:, :, 0], arr190[:, :, 1], arr190[:, :, 2]

    lid_left = 0.128 + yn * 0.095
    lid_right = 0.872 - yn * 0.095
    in_lid = (yn <= 0.232) & (xn >= lid_left) & (xn <= lid_right)
    in_hinge_bridge = (yn > 0.220) & (yn < 0.276) & (((xn >= 0.225) & (xn <= 0.468)) | ((xn >= 0.532) & (xn <= 0.775)))

    t_base = np.clip((yn - 0.272) / (0.800 - 0.272), 0.0, 1.0)
    base_left = np.where(yn <= 0.800, 0.140 - t_base * 0.066, 0.074 + ((yn - 0.800) / 0.085) * 0.032)
    base_right = np.where(yn <= 0.800, 0.860 + t_base * 0.066, 0.926 - ((yn - 0.800) / 0.085) * 0.032)
    in_base = (yn >= 0.272) & (yn <= 0.884) & (xn >= base_left) & (xn <= base_right)
    in_latches = (yn > 0.860) & (yn <= 0.928) & (((xn >= 0.205) & (xn <= 0.365)) | ((xn >= 0.610) & (xn <= 0.768))) & (lum190 < 90)
    is_model = in_lid | in_hinge_bridge | in_base | in_latches

    # 1. Accent: 2 orange hinge pins
    raw_acc = is_model & (r - b > 28) & (r > g)
    m_acc = dilate(raw_acc, 3) & is_model & (r - b > 12)

    # 2. Secondary: 3D difference between 190 and 184 isolates the 9 removable dividers, plus hinges & front latches
    diff_div = np.abs(arr190 - arr184).max(axis=2)
    in_cavity = (yn > 0.278) & (yn < 0.780) & (xn > 0.13) & (xn < 0.87)
    dividers = in_cavity & (diff_div > 18) & (lum190 < 125)
    dividers = close_holes(dividers, 5) & in_cavity

    hinges = is_model & (~m_acc) & (yn > 0.10) & (yn < 0.39) & (xn > 0.22) & (xn < 0.78) & (lum184 < 112)
    hinges = close_holes(hinges, 7) & is_model & (~m_acc)

    latch_boxes = (yn > 0.785) & (yn <= 0.928) & (((xn >= 0.205) & (xn <= 0.365)) | ((xn >= 0.610) & (xn <= 0.768))) & (lum190 < 135)
    front_hw = (is_model & (yn > 0.76) & (lum190 < 96)) | (is_model & latch_boxes)
    front_hw = close_holes(front_hw, 7) & is_model
    m_sec = (dividers | hinges | front_hw) & (~m_acc)
    m_pri = is_model & (~m_acc) & (~m_sec)

    save_render_and_mask(
        '09-sustainer-interior',
        'Open Sustainer: Dividers, Hinges & Latches (Studio)',
        'Studio close-up of open Sustainer showing Shell & Lid (Primary), 9 Dividers + Hinges + Latches (Secondary), and Hinge Pins (Accent)',
        Image.fromarray(arr190.astype(np.uint8)), m_pri, m_sec, m_acc
    )


def process_studio_roof_gridfinity(web_dir: Path):
    p_roof = web_dir / 'roof-gridfinity.png'
    if not p_roof.exists():
        return

    im = Image.open(p_roof).convert('RGB')
    w0, h0 = im.size
    c10 = (0.16, 0.04, 0.84, 0.98)
    arr = np.array(im.crop((
        int(w0 * c10[0]), int(h0 * c10[1]),
        int(w0 * c10[2]), int(h0 * c10[3])
    )).resize((880, 680), Image.Resampling.LANCZOS)).astype(float)
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yn, xn = yy / float(h), xx / float(w)
    lum = arr.mean(axis=2)

    t_roof = np.clip((yn - 0.045) / (0.575 - 0.045), 0.0, 1.0)
    roof_left = 0.160 - t_roof * 0.068
    roof_right = 0.840 + t_roof * 0.068
    t_body = np.clip((yn - 0.575) / (0.980 - 0.575), 0.0, 1.0)
    body_left = 0.102 + t_body * 0.118
    body_right = 0.898 - t_body * 0.118

    in_tower = np.where(
        yn <= 0.575,
        (yn >= 0.042) & (xn >= roof_left) & (xn <= roof_right),
        (yn <= 0.982) & (xn >= body_left) & (xn <= body_right)
    )
    is_model = in_tower & ((lum > 105) | ((yn > 0.14) & (xn > body_left + 0.02) & (xn < body_right - 0.02)))

    handle_box = (yn > 0.145) & (yn < 0.348) & (xn > 0.335) & (xn < 0.665)
    m_handle = handle_box & (lum < 135)
    m_handle = close_holes(m_handle, 9) & handle_box

    center_seam = (np.abs(xn - 0.50) < 0.025) & (yn > 0.58) & (yn < 0.81)
    lower_hw = is_model & (~center_seam) & (yn > 0.60) & (lum < 102)
    lower_hw = close_holes(lower_hw, 5) & is_model & (lum < 125)

    m_sec = m_handle | lower_hw
    m_pri = is_model & (~m_sec)
    m_acc = np.zeros_like(m_pri)

    save_render_and_mask(
        '10-roof-gridfinity',
        'Gridfinity Roof & Carry Handle (Studio)',
        'Top-down studio view of Gridfinity Roof & Dual S-Drawers (Primary) with Top Carry Handle, Lock Gears & Latches (Secondary)',
        Image.fromarray(arr.astype(np.uint8)), m_pri, m_sec, m_acc
    )


if __name__ == '__main__':
    load_dotenv(ROOT_DIR / '.env')
    vault_dir_str = os.environ.get('VAULT_USSA_DIR', '')
    vault_dir = Path(vault_dir_str).expanduser() if vault_dir_str else None
    ensure_assets(vault_dir)
    web_dir = ASSETS_DIR / 'web'

    process_grey_bg_exploded(
        ASSETS_DIR / 'drawers-exploded.png',
        '01-drawer-exploded',
        'Exploded Drawer Module (S3 1F)',
        'Shows all 3 color zones: Shell/Roof/Facade (Primary), Box/Handle/Lock/Slides (Secondary), Springs/Latch/Rails/Stoppers (Accent)',
        (0.27, 0.06, 0.71, 0.94), (960, 672), sec_max_lum=96
    )
    process_studio_stacks(web_dir)
    process_studio_drawer_interior(web_dir)
    process_studio_sustainer_interior(web_dir)
    process_studio_roof_gridfinity(web_dir)
    process_white_bg_render(
        ASSETS_DIR / 'manual-003.png',
        '02-both-types',
        'Drawer & Sustainer Side-by-Side',
        'Assembled S-Drawer with Gridfinity Roof & Handle next to top-opening Sustainer Case',
        (0.08, 0.12, 0.92, 0.92), (840, 800), mode='both_types'
    )
    process_white_bg_render(
        ASSETS_DIR / 'manual-007.png',
        '03-interiors-grid',
        'All 7 Interior Configurations',
        'Sustainers & Drawers with Gridfinity Bins (Accent), Dividers (Secondary), and Outer Shells (Primary)',
        (0.03, 0.16, 0.97, 0.84), (960, 688), mode='interiors'
    )
    process_white_bg_render(
        ASSETS_DIR / 'drawer-step-001.png',
        '04-springs-lock',
        'Facade Mechanism Close-Up',
        'Internal view of the S1F Facade (Primary), Key Lock Gear (Secondary), and Leaf Springs (Accent)',
        (0.08, 0.40, 0.92, 0.94), (860, 560), mode='default'
    )
    process_white_bg_render(
        ASSETS_DIR / 'drawer-step-007.png',
        '05-latch-stoppers',
        'Closed Module & Bottom Latch',
        'Shows how the Accent color peeks through the side Runner Stopper slots and underside Latch',
        (0.06, 0.10, 0.94, 0.92), (860, 760), mode='latch_stoppers'
    )
    process_grey_bg_exploded(
        ASSETS_DIR / 'sustainers-exploded.png',
        '06-sustainer-exploded',
        'Exploded Sustainer Cases (L3 1F & 2F)',
        'Top-opening Sustainer shells & roofs (Primary), hinges/latches/dividers (Secondary), and hinge rods (Accent)',
        (0.22, 0.06, 0.76, 0.94), (960, 672), sec_max_lum=88
    )

    out_js = ROOT_DIR / 'renders-data.js'
    out_js.write_text('window.VAULT_RENDERS = ' + json.dumps(renders_bundle) + ';\n', encoding='utf-8')
    print(f'Wrote {out_js} successfully!')

