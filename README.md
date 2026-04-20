# Pens

This repo generates parametric CAD models from YAML configs and publishes a small **GitHub Pages** gallery from the same files.

## Structure

- `configurations/` — one YAML file per pen variant (metrics, gallery paths, copy for the site)
- `assets/` — images used by the gallery (referenced from each config’s `gallery` list)
- `cad/` — CadQuery model (`engine.build(config)` reads `config["metrics"]`)
- `scripts/` — `build.py` (STEP export), `generate_site_data.py` (writes `site/data.json`)
- `site/` — static gallery (`index.html`, `styles.css`, `app.js`)
- `outputs/` — generated `.step` (and later `.stl` / `.gcode` when you add them to the same folder)

## Getting started (Dev Container)

1. Install Docker + VS Code  
2. Open the repo in VS Code  
3. **Reopen in Container**  
4. Build CAD and refresh site data:

```bash
python scripts/build.py
python scripts/generate_site_data.py
```

Open `site/index.html` in a browser via a local static server (so `fetch("./data.json")` works), for example:

```bash
python -m http.server 8080 --directory site
```

## Configuration format

Each file under `configurations/` drives both the CAD build and the gallery.

| Field | Required | Purpose |
| --- | --- | --- |
| `id` | yes | Stable slug (should match `output.name` and the config filename stem). |
| `title` | yes | Heading on the gallery card. |
| `description` | no | Short blurb on the card. |
| `metrics` | yes | Numbers passed into `cad/engine.py`. |
| `output.name` | no | STEP basename **without** version; defaults to the YAML filename stem. |
| `gallery` | no | List of image paths (repo-relative, usually under `assets/…`). |

Release **version** for filenames still comes from the Git tag in CI (`PENS_RELEASE_VERSION`), or from `git describe` / `dev` locally — not from YAML.

## GitHub Pages

1. Repo **Settings → Pages**  
2. **Build and deployment**: Source = **GitHub Actions**  
3. Push to `main` (or run **Deploy GitHub Pages** manually). The workflow builds STEP files, writes `site/data.json`, and uploads `site/` + `assets/` + `outputs/` as the published site.

Download buttons on the site link to `outputs/*.step` (and `*.stl` / `*.gcode` when those files exist next to the STEP after a build).

## Pages CMS

This repo includes [`.pages.yml`](.pages.yml) so you can use **[Pages CMS](https://pagescms.org)** against the same GitHub repository: connect the repo in Pages CMS, edit the **Pen configurations** collection, upload gallery images into **`assets/`**, and commit changes from the UI — no code edits required to add a new variant.

Use the same `id` for the entry, `output.name`, and the saved filename stem (for example `pen_acme.yml` with `id: pen_acme` and `output.name: pen_acme`).

## Future work

Slicer profiles (`slicer/`), `cad/utils.py`, and richer CMS fields can be added without changing the overall layout.
