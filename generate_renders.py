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
    if all(p.exists() for p in required):
        return

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


def morph_open(mask_bool, size=5, dilate_extra=3):
    img = Image.fromarray((mask_bool.astype(np.uint8) * 255))
    if size > 1:
        img = img.filter(ImageFilter.MinFilter(size))
        img = img.filter(ImageFilter.MaxFilter(size))
    if dilate_extra > 1:
        img = img.filter(ImageFilter.MaxFilter(dilate_extra))
    img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
    return np.array(img).astype(float) / 255.0


renders_bundle = {}


def save_render_and_mask(name, title, subtitle, img, mask_r, mask_g, mask_b):
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    mr = Image.fromarray((np.clip(mask_r, 0, 1) * 255).astype(np.uint8))
    mg = Image.fromarray((np.clip(mask_g, 0, 1) * 255).astype(np.uint8))
    mb = Image.fromarray((np.clip(mask_b, 0, 1) * 255).astype(np.uint8))
    mask_img = Image.merge('RGB', (mr, mg, mb))
    img.save(RENDERS_DIR / f'{name}.png', optimize=True)
    mask_img.save(RENDERS_DIR / f'{name}-mask.png', optimize=True)

    buf_img = io.BytesIO()
    img.save(buf_img, format='WEBP', quality=90)
    b64_img = 'data:image/webp;base64,' + base64.b64encode(buf_img.getvalue()).decode('ascii')

    buf_mask = io.BytesIO()
    mask_img.save(buf_mask, format='WEBP', quality=92)
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


def process_grey_bg_exploded(src_path, out_name, title, subtitle, crop_box, out_size):
    img_full = Image.open(src_path).convert('RGB')
    w, h = img_full.size
    crop = img_full.crop((int(w*crop_box[0]), int(h*crop_box[1]), int(w*crop_box[2]), int(h*crop_box[3]))).resize(out_size, Image.Resampling.LANCZOS)
    arr = np.array(crop).astype(float)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    sat = np.maximum(np.maximum(r,g),b) - np.minimum(np.minimum(r,g),b)
    lum = (r + g + b) / 3.0
    bg_dist = np.sqrt((r - 157)**2 + (g - 163)**2 + (b - 170)**2)
    coolness = b - r

    raw_accent = (r - b > 22) & (r > g)
    m_acc = morph_open(raw_accent, size=3, dilate_extra=3)

    raw_dark = (sat < 22) & (lum >= 25) & (lum <= 96) & (bg_dist > 32)
    m_sec = morph_open(raw_dark, size=5, dilate_extra=3) * (1.0 - m_acc)

    raw_light = (sat < 20) & (coolness < 7.0) & (bg_dist > 8.5) & (lum > 96)
    m_pri = morph_open(raw_light, size=5, dilate_extra=3) * (1.0 - m_acc) * (1.0 - m_sec)

    save_render_and_mask(out_name, title, subtitle, crop, m_pri, m_sec, m_acc)


def process_white_bg_render(src_path, out_name, title, subtitle, crop_box, out_size, mode='default'):
    img_full = Image.open(src_path).convert('RGB')
    w, h = img_full.size
    crop = img_full.crop((int(w*crop_box[0]), int(h*crop_box[1]), int(w*crop_box[2]), int(h*crop_box[3]))).resize(out_size, Image.Resampling.LANCZOS)
    arr = np.array(crop).astype(float)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    sat = np.maximum(np.maximum(r,g),b) - np.minimum(np.minimum(r,g),b)
    lum = (r + g + b) / 3.0
    yy, xx = np.mgrid[0:out_size[1], 0:out_size[0]]

    raw_accent = (r - b > 28) & (r > g)
    if mode == 'both_types':
        arrow_top = (xx > out_size[0]*0.60) & (yy < out_size[1]*0.45)
        arrow_inner = (xx > out_size[0]*0.42) & (xx < out_size[0]*0.60) & (yy > out_size[1]*0.68) & (yy < out_size[1]*0.83)
        raw_accent = raw_accent & (~arrow_top) & (~arrow_inner)
    m_acc = morph_open(raw_accent, size=3, dilate_extra=3)

    dark_max = 95 if mode == 'both_types' else 112
    raw_dark = (sat < 25) & (lum >= 22) & (lum <= dark_max)
    if mode == 'latch_stoppers':
        ui_arrows = ((xx > out_size[0]*0.41) & (xx < out_size[0]*0.61)) | ((xx > out_size[0]*0.21) & (xx < out_size[0]*0.29) & (yy > out_size[1]*0.55) & (yy < out_size[1]*0.72))
        raw_dark = raw_dark & (~ui_arrows)
    m_sec = morph_open(raw_dark, size=5, dilate_extra=3) * (1.0 - m_acc)

    light_max = 222 if mode == 'both_types' else 234
    raw_light = (sat < 22) & (lum > dark_max) & (lum < light_max)
    if mode == 'latch_stoppers':
        ui_arrows = (xx > out_size[0]*0.41) & (xx < out_size[0]*0.61)
        raw_light = raw_light & (~ui_arrows)
    m_pri = morph_open(raw_light, size=5, dilate_extra=3) * (1.0 - m_acc) * (1.0 - m_sec)

    save_render_and_mask(out_name, title, subtitle, crop, m_pri, m_sec, m_acc)


if __name__ == '__main__':
    load_dotenv(ROOT_DIR / '.env')
    vault_dir_str = os.environ.get('VAULT_USSA_DIR', '')
    vault_dir = Path(vault_dir_str).expanduser() if vault_dir_str else None
    ensure_assets(vault_dir)

    process_grey_bg_exploded(
        ASSETS_DIR / 'drawers-exploded.png',
        '01-drawer-exploded',
        'Exploded Drawer Module (S3 1F)',
        'Shows all 3 color zones: Shell/Roof/Facade (Primary), Box/Handle/Lock/Slides (Secondary), Springs/Latch/Rails/Stoppers (Accent)',
        (0.27, 0.06, 0.71, 0.94), (960, 672)
    )
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
        (0.03, 0.16, 0.97, 0.84), (960, 688), mode='default'
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
        (0.22, 0.06, 0.76, 0.94), (960, 672)
    )

    out_js = ROOT_DIR / 'renders-data.js'
    out_js.write_text('window.VAULT_RENDERS = ' + json.dumps(renders_bundle) + ';\n', encoding='utf-8')
    print(f'Wrote {out_js} successfully!')
