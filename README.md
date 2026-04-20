# Pens

This repo generates parametric CAD models from YAML configs and publishes a small GitHub Pages gallery from the same files.

Live site: https://quintussential.com/pens/

## Structure

- `configurations/` - one YAML file per pen variant (dimensions, gallery paths, copy for the site)
- `assets/` - images used by the gallery (referenced from each config's `gallery` list)
- `cad/` - CadQuery model (`engine.build(config)` reads `config["dimensions"]`)
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
| `dimensions` | yes | Cylinder, frustum, and stepped-bore dimensions passed into `cad/engine.py`. |
| `output.name` | no | Optional STEP basename override; defaults to `id`. |
| `gallery` | no | List of image paths (repo-relative, usually under `assets/...`). |

The current model expects these `dimensions` keys:

- `cylinder_height`
- `cylinder_diameter`
- `frustum_height`
- `frustum_top_diameter`
- `frustum_bottom_diameter`
- `top_hole_diameter`
- `bottom_hole_diameter`
- `top_hole_height`

Release versions for filenames still come from the Git tag in CI (`PENS_RELEASE_VERSION`), or from `git describe` / `dev` locally, not from YAML.

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
