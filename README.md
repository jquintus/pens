# Pens

This repo generates parametric CAD models from YAML configs and publishes a small GitHub Pages gallery from the same files.

Live site: https://quintussential.com/pens/

## Structure

- `configurations/` - one YAML file per pen variant (`nose_cone`, gallery paths, copy for the site)
- `models/` - arbitrary CadQuery models. Each subfolder (e.g., `models/c_bracket/`) contains:
    - `config.yml`: Metadata (`id`, `title`, `description`) and a `model` section for parameters.
    - `model.py`: A Python script with a `build(model_config)` function that returns a CadQuery object.
- `assets/` - images used by the gallery
- `cad/` - CadQuery model (`engine.build(config)` reads `config["nose_cone"]`)
- `scripts/` - `build.py` (STEP + STL export), `generate_site_data.py` (writes `site/data.json`)
- `site/` - static gallery (`index.html`, `styles.css`, `app.js`)
- `outputs/` - generated `.step`, `.stl`, and later `.gcode` files

## Getting Started (Dev Container)

1. Install Docker + VS Code
2. Open the repo in VS Code
3. Reopen in Container
4. Build CAD and refresh site data:

```bash
python scripts/build.py
python scripts/generate_site_data.py
```

Open `site/index.html` in a browser via a local static server so `fetch("./data.json")` works, for example:

```bash
python -m http.server 8080 --directory site
```

## Configuration Format

Each file under `configurations/` drives both the CAD build and the gallery.

| Field | Required | Purpose |
| --- | --- | --- |
| `id` | yes | Stable slug and default output basename. |
| `title` | yes | Heading on the gallery card. |
| `description` | no | Short blurb on the card. |
| `nose_cone` | yes | Cylinder, frustum, and stepped-bore values passed into `cad/engine.py`. |
| `output.name` | no | Optional STEP basename override; defaults to `id`. |
| `gallery` | no | List of image paths (repo-relative, usually under `assets/...`). |

The current model expects these `nose_cone` keys:

- `cylinder_height`
- `cylinder_outside_diameter`
- `frustum_height`
- `frustum_top_diameter`
- `frustum_bottom_diameter`
- `top_hole_diameter`
- `bottom_hole_diameter`
- `top_hole_height`

Release versions for filenames still come from the Git tag in CI (`PENS_RELEASE_VERSION`), or from `git describe` / `dev` locally, not from YAML.

## Slicing & G-code

This project integrates PrusaSlicer to automatically generate printable G-code for each pen variant. By default, it generates two profiles:
- **Fast**: 0.15mm layer height, 10% grid infill (optimized for speed).
- **Quality**: 0.10mm layer height, 15% gyroid infill (optimized for detail).

Both profiles are configured for a **0.2mm nozzle**.

### Disabling Slicing

If you want to skip G-code generation (e.g., to speed up the build or if you don't have PrusaSlicer installed), you can disable it with a single line change:

1. Open `scripts/build.py`.
2. Comment out the `ENABLE_SLICING = True` line:
   ```python
   # ENABLE_SLICING = True
   ```

### Slicer Configurations

Custom slicer settings are stored as `.ini` files in the `slicer_configs/` directory.

## GitHub Pages

1. Repo Settings -> Pages
2. Build and deployment: Source = GitHub Actions
3. Push to `main` (or run `Deploy GitHub Pages` manually). The workflow builds STEP and STL files, writes `site/data.json`, and uploads `site/` + `assets/` + `outputs/` as the published site.

Generated CAD files are saved in `outputs/` in the repo workspace. During the Pages deploy job, that folder is copied into the published artifact as `_site/outputs/`, so the live site serves them from `outputs/...`.

Download buttons on the site link to `outputs/*.step` (and `*.stl` / `*.gcode` when those files exist next to the STEP after a build). The gallery uses the STL sidecar for the in-browser 3D preview while keeping STEP as the downloadable source artifact.

## Pages CMS

This repo includes [`.pages.yml`](.pages.yml) so you can use [Pages CMS](https://pagescms.org) against the same GitHub repository: connect the repo in Pages CMS, edit the Pen configurations collection, upload gallery images into `assets/`, and commit changes from the UI with no code edits required to add a new variant.

By default the saved filename stem and output basename come from `id`, so `pen_acme.yml` with `id: pen_acme` is enough. Only set `output.name` if you explicitly want a different basename.

## Future Work

Slicer profiles (`slicer/`), `cad/utils.py`, and richer CMS fields can be added without changing the overall layout.

## Parallel OpenSCAD gallery

The OpenSCAD gallery is published alongside the original at `/pens/openscad/`. Both use the same `configurations/` and `models/*/config.yml` files, so Pages CMS edits rebuild both versions. All nine current pen variants and the C-bracket have OpenSCAD implementations.

```sh
python -m pip install pyyaml
python scripts/build_openscad.py
python scripts/generate_openscad_site.py
```

Install OpenSCAD and put `openscad` on PATH, set `OPENSCAD`, or pass `--openscad /path/to/executable`. The macOS application path is detected automatically. Linux CI uses the packaged OpenSCAD under `xvfb-run`.

`cad/openscad/pen_parts.scad` and `models/c_bracket/model.scad` contain the geometry modules. Builds produce self-contained editable `.scad` files and printable `.stl` files under `outputs/openscad/`. Source downloads need no additional library installation. The models construct their rounded profiles explicitly rather than selecting edges after booleans.

OpenSCAD exports meshes, so this gallery offers SCAD and STL. Exact STEP exports remain in the original CadQuery gallery. Slice the STL in Bambu Studio using your installed nozzle and filament; this parallel build does not fabricate G-code printer headers.

Pages and release workflows build both backends. Releases attach the OpenSCAD files as `openscad-models.zip` to avoid colliding with the original STL asset names. The OpenSCAD validation workflow renders every config and checks closed geometry, component counts, portable source downloads, and gallery links. Legacy geometry is also checked against CadQuery dimensions and rounded volume; OpenSCAD-only shapes have their own geometry and clearance checks.

```sh
python -m pip install trimesh numpy cadquery
python -m unittest discover -s tests -v
```

For a local preview, copy `assets/` and `outputs/` into a temporary site directory beside the contents of `site/`, then serve that directory with `python -m http.server`.

## Refill measurements and designer

The `refills/` collection is edited in Pages CMS alongside the existing `configurations/` pen collection. Each refill YAML file describes one model or family. Put color and SKU specific URLs or notes in `variants`, so the physical shape is stored once. `format` means the physical refill family (for example, Parker-style G2); `brand` and `ink_type` describe different things. Photos are user-owned files uploaded through the existing `assets/` media workflow. Store external product URLs in `links` or `variants`; do not copy product photos into the repo or hotlink them.

The **writing tip is distance 0 mm**. List `segments` in order from the tip toward the rear. Every `end_distance_mm` is the distance from that same tip to the *end* of the segment, not the length of the segment itself. The segment length is derived by subtracting the previous end distance (or zero for the first segment). The last end distance is the refill's overall length. Measure with calipers from the tip each time, so an error in one section does not propagate through later sections.

Use `kind: cylinder` with `diameter_mm` and `end_distance_mm` for a constant diameter. Use `kind: taper` with `diameter_start_mm`, `diameter_end_mm`, and `end_distance_mm` for a tapered section. The taper diameters refer to the segment's two ends, moving from tip to rear. Both kinds can appear as often as needed. End distances must increase strictly, and known dimensions must be positive finite numbers.

Set `measurement_status` to `measured`, `approximate`, or `incomplete`. An individual segment can override that status and include `notes`. If a dimension is unknown, omit it and mark the refill or segment `incomplete`; the catalog retains the record, but the designer cannot use it for geometry until the profile is complete. A record with no measurements may use `segments: []` only when its status is `incomplete`. For uncertain but usable measurements, enter the value, mark it `approximate`, and explain the uncertainty in `measurement_notes`. `refills/example-refill.yml` is fictional example geometry, not verified commercial refill data.

The browser designer in the OpenSCAD gallery lets you inspect a refill, nose cone, end cap, and wooden body before exporting. Refill and nose bore profiles use the same three-column entry: starting diameter, ending diameter, and distance from the tip to the segment end. Leave either diameter blank for a cylinder; fill both for a taper. A blank row is always available for the next segment, so Tab moves through the measurements in order. The nose bore is initially derived from the refill and the two diameter clearances; choose **Customize bore** to edit its segments directly. The final bore end must equal the nose cone's visible plus insertion length.

The axial cutaway draws the refill inside the nose's hollow bore and body tube, and the designer checks their overlap before export. Body outside diameter and body length affect visualization only; they are omitted from printable geometry parameters. Download a self-contained SCAD source or save an exported configuration through its prefilled GitHub new-file link when available; the download fallback belongs under `configurations/`. New or edited refill YAML belongs under `refills/`. Subsequent edits can be made in the matching Pages CMS collection. The OpenSCAD-only geometry lives in optional `openscad` fields; the original CadQuery build continues to read `nose_cone` from the same configuration.
