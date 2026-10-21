# VAULT × Bambu Lab — Interactive Color & Material Design Studio

An interactive color visualizer, real-time 3D render color-swapper, and filament spool calculator for the **[VAULT by USSA](https://www.ussadesign.com/pages/vault?view=vault-model)** modular 3D-printed storage system, tailored for **Bambu Lab** filaments (`PLA Basic`, `PLA Matte`, and `PETG HF`).

👉 **[Launch Interactive Studio (GitHub Pages)](https://stari4ek.github.io/vault-color-studio/)**

---

## Features

1. **8 Curated Design Prospects**:
   * **Official USSA Promo**: `PLA Basic Light Gray (10104)` + `Dark Gray (10105)` + `Orange (10300)`
   * **Warm Studio / WFH Desk**: `PLA Matte Bone White (11103)` + `Charcoal (11101)` + `Terracotta (11203)`
   * **Concrete & Amber**: `PLA Matte Ash Gray (11102)` + `Charcoal (11101)` + `Sunflower Yellow (10402)`
   * **Stealth + Bright Trays**: `PLA Matte Charcoal (11101)` + `Light Gray (10104)` inner drawer trays (makes black M3/M4 bolts easy to spot) + `Orange (10300)`
   * Plus **Festool / Sys-Green**, **Botanical & Brass**, **Desert Sand & Black**, and **Machinist Blue Slate**.
2. **Real-Time 3D Render Color-Swapper**:
   * Recolors all 3 VAULT part zones (**Primary ~65%**, **Secondary ~30%**, **Accent ~5%**) across 6 official diagrams while preserving ambient occlusion shadows and bevel highlights.
   * Includes a **Before / After Split Slider**, **Hold to See Original Promo**, and **Invert Primary / Secondary**.
   * Works both hosted on GitHub Pages and offline via `file://` (double-clicking `index.html`) with zero CORS/canvas tainting.
3. **Shareable Links, PNG Export & Shopping List Copy**:
   * **🔗 Share Combo Link**: Automatically encodes your Primary, Secondary, Accent, and active render in the URL (`?p=10104&s=10105&a=10300`) so you can share colorways on Reddit, MakerWorld, or Discord.
   * **📷 Save Render PNG**: Downloads the recolored 3D render with a bottom specification legend bar showing the exact Bambu Lab filament names & SKUs.
   * **📋 Copy Shopping List**: One-click clipboard copy of your filament SKUs, gram weights, and 1kg spool counts.
4. **Closet Shelf vs. WFH Office Stack Visualizer**:
   * Side-by-side vector preview of compact `S3`/`S4` closet bolt drawers (with optional fastener category color tags) next to larger `L`/`XL` modules and top-opening Sustainers on a home-office credenza.

---

## Quick Start

### 1. Open the Visualizer Directly
Simply open [`index.html`](index.html) in any browser:
```sh
open index.html
```

### 2. Regenerating Renders from Your Local USSA VAULT Archive
If you own the USSA VAULT STL/PDF archive and want to extract/regenerate the renders and RGB zone masks:

1. Copy `.env.example` to `.env` and set `VAULT_USSA_DIR` to your unzipped VAULT archive directory:
   ```sh
   cp .env.example .env
   # Edit .env: VAULT_USSA_DIR="/path/to/vault-ussa"
   ```
   *(Or pass `VAULT_USSA_DIR` directly as an environment variable.)*
2. Run the generator script (requires Python 3 with `Pillow`, `numpy`, and `poppler`/`pdfimages` if extracting fresh PDF pages):
   ```sh
   python3 generate_renders.py
   ```
   This extracts the diagrams from `$VAULT_USSA_DIR`, computes the RGB multi-zone masks (`renders/*-mask.png`), and writes `renders-data.js`.

---

## License & Attribution

* **VAULT Storage System** design, STL models, and manual renders are property of **[USSA Design](https://www.ussadesign.com/pages/vault)**. Raw archive files (`VAULT_USSA_DIR`) are not distributed in this repository.
* **Color Studio Code** (`index.html`, `generate_renders.py`) is open-source for the 3D printing community.
