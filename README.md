# VAULT — Filament & Color Design Studio

An interactive color visualizer, real-time 3D render color-swapper, and filament spool calculator for the **[VAULT by USSA](https://www.ussadesign.com/pages/vault?view=vault-model)** modular 3D-printed storage system, featuring **199 filaments across 7 popular brands**: **Bambu Lab** (68), **Polymaker** (28), **Prusament** (22), **eSUN** (21), **SUNLU** (20), **ELEGOO** (20), and **Overture** (20).

👉 **[Launch Interactive Studio (GitHub Pages)](https://stari4ek.github.io/vault-color-studio/)**

---

## Features

1. **18 Curated Color Presets (Promo Video, Studio/Workshop & Multi-Brand)**:
   * **Official USSA Promo**: `Bambu Lab PLA Basic Light Gray (10104)` + `Dark Gray (10105)` + `Orange (10300)`
   * **6 Promo Video Colorways**: **Apple Green & Orange** (`11502` + `10100` + `10300`), **Sakura Pink & White** (`11201`), **Indigo Purple & White** (`10701`), **Olive Sage & White** (`11501`), **Dark Blue & White** (`11602`), and **Studio Gray & Dark** (`11102`)
   * **Studio & Workshop Setups**: **Warm Studio / WFH Desk**, **Concrete & Amber**, **Stealth + Bright Trays**, **Festool / Sys-Green**, **Botanical & Brass**, **Desert Sand & Black**, and **Machinist Blue Slate**.
   * **Multi-Brand Editions**: **Prusa Signature Edition** (`Prusament Galaxy Black` + `Anthracite Grey` + `Prusa Orange PETG`), **PolyTerra Earth Studio** (`Polymaker`), **eSUN Tactical & Peak**, and **Space Grey & Fire Red** (`ELEGOO + eSUN`).
2. **Real-Time 3D Render Color-Swapper**:
   * Recolors all 3 VAULT part zones (**Primary ~65%**, **Secondary ~30%**, **Accent ~5%**) across 10 official diagrams & studio renders while preserving ambient occlusion shadows and bevel highlights.
   * Includes a **Before / After Split Slider**, **Hold to See Original Promo**, and **Invert Primary / Secondary**.
   * Works both hosted on GitHub Pages and offline via `file://` (double-clicking `index.html`) with zero CORS/canvas tainting.
3. **Shareable Links, PNG Export & Shopping List Copy**:
   * **🔗 Share Combo Link**: Automatically encodes your Primary, Secondary, Accent, and active render in the URL (`?p=10104&s=10105&a=10300`) so you can share colorways on Reddit, MakerWorld, Printables, or Discord.
   * **📷 Save Render PNG**: Downloads the recolored 3D render with a bottom specification legend bar showing the exact filament brand, material, color name & SKU.
   * **📋 Copy Shopping List**: One-click clipboard copy of your filament SKUs, gram weights, and 1kg spool counts.
4. **Closet Shelf vs. WFH Office Stack Visualizer**:
   * Side-by-side vector preview of compact `S3`/`S4` closet bolt drawers (with optional fastener category color tags) next to larger `L`/`XL` modules and top-opening Sustainers on a home-office credenza.

---

## Filament Reference Catalogs (`filaments/`)

Each supported filament brand is documented in its own Markdown table under [`filaments/`](filaments/) for easy reference and community pull requests:

* **[Bambu Lab (`filaments/bambulab.md`)](filaments/bambulab.md)** — 68 colors (`PLA Basic`, `PLA Matte`, `PETG Basic`)
* **[Polymaker (`filaments/polymaker.md`)](filaments/polymaker.md)** — 28 colors (`PolyTerra / Panchroma Matte`, `PolyLite PLA`, `PolyLite PETG`)
* **[Prusament (`filaments/prusament.md`)](filaments/prusament.md)** — 22 colors (`Prusament PLA`, `PLA Matte`, `Prusament PETG`)
* **[eSUN (`filaments/esun.md`)](filaments/esun.md)** — 21 colors (`PLA+`, `ePLA-Matte`, `PETG`)
* **[SUNLU (`filaments/sunlu.md`)](filaments/sunlu.md)** — 20 colors (`PLA+`, `PLA Matte`, `PETG`)
* **[ELEGOO (`filaments/elegoo.md`)](filaments/elegoo.md)** — 20 colors (`Rapid PLA+`, `PLA Matte`, `Rapid PETG`)
* **[Overture (`filaments/overture.md`)](filaments/overture.md)** — 20 colors (`PLA+`, `Matte PLA`, `PETG`)

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
