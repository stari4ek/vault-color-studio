# AGENTS.md — USSA "VAULT" Bambu Lab Color Studio & Domain Guide

This repository (`vault-color-studio`) contains the interactive **Bambu Lab Filament & Color Design Prospect Studio** for the **VAULT by USSA** modular 3D-printed storage system (`https://www.ussadesign.com/pages/vault?view=vault-model`).

The raw USSA VAULT STL & PDF archive is kept separate and referenced via the `VAULT_USSA_DIR` environment variable or local `.env` file.

---

## 1. Repository & External Archive Structure

### Color Studio Repository (`vault-color-studio/`)
```text
vault-color-studio/
├── AGENTS.md                  # Project & domain guide for engineers and AI agents
├── README.md                  # User-facing setup & publishing documentation
├── bambulab-filaments.md      # Reference catalog of 68 Bambu Lab filaments (PLA Basic, PLA Matte, PETG Basic)
├── LICENSE                    # MIT License for studio code
├── .env.example               # Template for VAULT_USSA_DIR configuration
├── .env                       # Local untracked config (VAULT_USSA_DIR="/path/to/vault-ussa")
├── .gitignore                 # Ignores .env, raw extracted assets/, OS/Python cache
├── index.html                 # Single-page app (works directly via file:// or GitHub Pages)
├── generate_renders.py        # Python (PIL + NumPy) pipeline reading VAULT_USSA_DIR to build masks & renders-data.js
├── renders-data.js            # Base64-encoded WebP renders + RGB zone masks (prevents file:// Canvas CORS errors)
├── renders/                   # Cropped PNG renders and *-mask.png RGB zone maps
└── assets/                    # Untracked raw extracted PNGs from $VAULT_USSA_DIR PDFs & Naming diagrams
```

### External USSA VAULT Archive (`$VAULT_USSA_DIR`)
```text
$VAULT_USSA_DIR/
├── 01_Instructions Manual.pdf # Master overview, hardware BOM, sizing matrix, and print notes
├── 02_Drawer Assembly.pdf     # Step-by-step assembly & slicer text guide for Drawers
├── 03_Sustainers Assembly.pdf # Step-by-step assembly guide for top-opening Sustainers
├── 04_Modifications.pdf       # Assembly for Backbone, Wheels, Feet, Pull-out Handles
├── 05_Mounting Instructions.pdf # Wall mounts, under-table mounts, and pegboards (USSA & IKEA Skadis)
├── 01. DRAWERS/               # Drawer STL files (01. S Families .. 06. XL² Families, 07. Universal, Drawers Naming.png)
├── 02. SUSTAINERS/            # Top-opening case STL files (01. S Families .. 04. XL Families, 05. Universal, Sustainer Naming.png)
└── 03. MODIFICATIONS/         # Mobile cart & mounting STL files (Backbone, Base, Feet, Wheels, Wall Mounts, XL Mods Naming.png)
```

---

## 2. VAULT System Architecture & Sizing Matrix

### Two Core Module Types
1. **Drawers (`$VAULT_USSA_DIR/01. DRAWERS/`)**: Front-sliding drawer boxes inside stackable outer shells. Locked via a rotary central `Key Lock` gear that drives dual `Springs.stl` into side `Geared Rails` (`optional` for extra locking force or multi-drawer 2F/4F modules).
2. **Sustainers (`$VAULT_USSA_DIR/02. SUSTAINERS/`)**: Top-opening cases (Systainer-style) with rear `Hinges` + printed `Rods` and front `Lock Inner/Outer Parts`. Available in Flat, Gridfinity Base, Dividers, or Sealed Divider interiors.

### Dimensional System (50 Size Variants / 160 Module Variants)
* **4 Widths**: `S`, `M`, `L`, `XL` (plus dual-bay `L²` and `XL²` for drawers).
  * **Stacking math**:
    * `L` width = `S + S` (two `S` modules stack side-by-side on top of one `L` module).
    * `XL` width = `S + M` (one `S` + one `M` module stack side-by-side on top of one `XL` module).
* **5 Depths**: `3`, `4`, `5`, `6`, `7` — determined by **Gridfinity units** (`42mm × 3`, `42mm × 4`, etc.).
* **3 Heights**: `1F`, `2F`, `4F` (no `3F` so heights always divide/combine evenly by 2 without stack gaps).

### Hardware BOM Summary (from `01_Instructions Manual.pdf` Page 3)
* **Drawers**:
  * `M4 × 14mm` bolts: `4×` per `1F` floor (`6×` for `2F`/`4F` facades)
  * `M6 × 50mm` bolts: `2×` per roof handle
* **Sustainers**:
  * `M4 × 10mm` bolts (`8×`), `M4 × 14mm` bolts (`16×`), `M4 × 20mm` bolts (`7×`) per module
* **Modifications / Mobile Cart**:
  * Uses `M16` rods (`248mm` for S, `338mm` for M, `414mm` for L, `504mm` for XL), `6205ZZ` bearings, `SCSAW` stoppers, `M6×8×8` heat-set inserts, and `M8` caster holes.

---

## 3. Color Zones & Bambu Lab Material Guidelines

### Official USSA Promo Spec (`01_Instructions Manual.pdf` Page 1)
* **Main Shell Grey**: **Bambu Lab PLA Basic — Light Gray (`10104`, `#D1D3D5`)**.
* **Secondary Dark Grey**: **Bambu Lab PLA Basic — Dark Gray (`10105`, `#545454`)** (or Charcoal `11101`).
* **Mechanical Accent**: **Bambu Lab PLA Basic — Orange (`10300`, `#FF6A13`)**.
* **Tires (`Tyre (TPU).stl`)**: **Bambu Lab TPU** (7 walls/perimeters recommended in Bambu Studio).

### 3-Zone Part Breakdown & Weight Distribution
1. **Primary Zone (~65% of filament weight)**:
   * **Parts**: Outer Module Shells (`S3 1F Module`), Roofs (`Grid Roof`, `Table Roof`, `Bowl Roof`), Front Facades (`S1F Facade`), `Runner Guides`, `Facade Cap`, `Key Cap`, Sustainer `Lock Holder` & pins.
   * **Material**: `Bambu PLA Basic` or `Bambu PLA Matte` (Matte hides layer lines well for WFH office modules).
2. **Secondary Zone (~30% of filament weight)**:
   * **Parts**: Inner Drawer Boxes (`S3 Box 1F`), `Top Handle`, `Key Lock`, `Runner Slides`, Sustainer `Hinges`, `Lock Outer/Inner Parts`, `Dividers`, and `Backbone`.
   * **Material**: Use **PLA Basic** (or **PETG Basic**) for `Runner Slides` and `Key Lock` for low friction and wear resistance.
3. **Accent Zone (~5% of filament weight)**:
   * **Parts**: `Springs.stl`, `Latch.stl` (bottom stacking latch), `Runner Stoppers` (visible through side slots), `Geared Rails`, Sustainer `Rods`, and internal Gridfinity bins.
   * **Material**: **MUST use Bambu PLA Basic or PETG Basic** for `Springs.stl`, `Latch.stl`, and `Geared Rails`. Avoid `PLA Matte` on compliant springs/latches as it creeps and loses spring tension over time.

### Parts Requiring Slicer Supports
Files explicitly named `(Turn On Supports)` in `$VAULT_USSA_DIR/01. DRAWERS/07. Universal/` and `Facades/`:
* `S1F.stl`, `S2F.stl`, `S4F.stl` (and M/L/XL Facades)
* `Key (Turn On Supports).stl`, `Hidden Key (Turn On Supports).stl`, `Hidden Key Part 2 (Turn on Supports).stl`
* `Top Handle (Turn On Supports).stl`
* Note: Inner Drawer Boxes and Sustainers have built-in breakaway manual support strips along the side runner/divider slots (see `02_Drawer Assembly.pdf` page 3 and `03_Sustainers Assembly.pdf` page 6) that must be snapped off before assembly.

---

## 4. Interactive Color Studio Technical Notes

### Configuration (`VAULT_USSA_DIR`)
* `generate_renders.py` reads `VAULT_USSA_DIR` from the environment or `.env` file in the repository root.
* If `./assets/` is empty or missing source PNGs, `generate_renders.py` automatically runs `pdfimages -png` on `$VAULT_USSA_DIR/01_Instructions Manual.pdf` and `$VAULT_USSA_DIR/02_Drawer Assembly.pdf` and copies the high-res exploded naming PNGs into `./assets/`.

### How the Real-Time Render Color-Swapper Works
* **Zero-Server `file://` Compatibility**: Modern browsers block `ctx.getImageData()` on `<canvas>` elements when images are loaded from relative `file://` URLs (`SecurityError: Tainted canvas`). To ensure `index.html` works out-of-the-box by double-clicking it in Finder (as well as over HTTP), `generate_renders.py` encodes both the cropped renders and their RGB zone masks as `data:image/webp;base64,...` strings inside `renders-data.js` (`window.VAULT_RENDERS`).
* **RGB Multi-Zone Mask Convention (`renders/*-mask.png`)**:
  * **Red channel (`R`)** = `0..255` alpha weight for **Primary** parts.
  * **Green channel (`G`)** = `0..255` alpha weight for **Secondary** parts.
  * **Blue channel (`B`)** = `0..255` alpha weight for **Accent** parts.
* **Shading-Preserving Transfer Function (`shadeChannel` in `index.html`)**:
  * Computes perceived luminance `L = 0.299*R + 0.587*G + 0.114*B` of each original pixel and maps it relative to each zone's reference luminance in the original render (`basePri = 196`, `baseSec = 72`, `baseAcc = 142`), preserving ambient occlusion shadows and specular bevel highlights even when swapping between light and dark filaments.

### Browser Support Policy
* **Browser Support**: Allow Baseline Widely Available and modern Canvas/CSS features (`color-mix(in oklab, ...)`, CSS custom properties, HTML5 Canvas 2D `ImageData`), maintaining compatibility with `file://` local execution on macOS Safari and Chrome without external npm/bundler runtime dependencies.
