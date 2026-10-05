#!/usr/bin/env python3
"""Generate a parallel OpenSCAD gallery from the existing CMS configurations.

Run after build_openscad.py. Published paths share assets, styles and the STL
viewer with the CadQuery gallery; only OpenSCAD STL and portable SCAD are offered.
"""

from html import escape
import json
from pathlib import Path
from urllib.parse import quote

from config_utils import CONFIG_DIR, OUTPUT_DIR, REPO_ROOT, SITE_DIR, load_config, output_stem
from generate_site_data import MODELS_DIR, normalize_gallery_paths

GALLERY_DIR = SITE_DIR / "openscad"


def html(value):
    return escape(str(value), quote=True)


def script_json(value):
    # JSON in a script element must not contain a closing script tag.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(
        ">", "\\u003e"
    ).replace("&", "\\u0026")


def url(path):
    return quote(str(path), safe="/")


def configurations():
    paths = sorted(CONFIG_DIR.glob("*.yml")) + sorted(CONFIG_DIR.glob("*.yaml"))
    for path in paths:
        if not path.name.startswith("."):
            yield path, True
    for folder in sorted(MODELS_DIR.iterdir()) if MODELS_DIR.exists() else []:
        if not folder.is_dir():
            continue
        for name in ("config.yml", "config.yaml"):
            path = folder / name
            if path.is_file():
                yield path, False
                break


def entry(path, is_pen):
    config = load_config(path)
    slug = path.stem if is_pen else path.parent.name
    stem = output_stem(path, config)
    downloads = {}
    for extension in ("stl", "scad"):
        artifact = OUTPUT_DIR / "openscad" / f"{stem}.{extension}"
        downloads[extension] = f"outputs/openscad/{artifact.name}" if artifact.is_file() else None
    return {
        "slug": slug,
        "id": str(config.get("id") or slug),
        "title": str(config.get("title") or slug.replace("_", " ").title()),
        "description": str(config.get("description") or ""),
        "parameters": config.get("nose_cone" if is_pen else "model") or {},
        "images": normalize_gallery_paths(config),
        "downloads": downloads,
    }


def header(title, shared_prefix, local_prefix, cadquery_path):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html(title)} — OpenSCAD Pens</title>
  <link rel="stylesheet" href="{shared_prefix}styles.css">
  <link rel="stylesheet" href="{local_prefix}styles.css">
</head>
<body>
<div class="bg-grid" aria-hidden="true"></div>
<header class="site-header"><div class="site-header__inner">
  <a class="brand-link" href="{local_prefix}index.html"><div class="brand">
    <span class="brand__mark" aria-hidden="true"></span>
    <div><h1 class="brand__title">Pens · OpenSCAD</h1>
    <p class="brand__tag">Parametric configs to printable models</p></div>
  </div></a>
  <nav class="quick-links" aria-label="Quick links">
    <a class="quick-links__item" href="{html(cadquery_path)}">CadQuery version</a>
    <a class="quick-links__item" href="https://app.pagescms.org/jquintus/pens/" rel="noreferrer">Edit configurations</a>
  </nav>
</div></header>'''


def metrics(parameters, limit=None):
    items = list(parameters.items())
    if limit is not None:
        items = items[:limit]
    return "".join(
        f"<li>{html(key.replace('_', ' '))}: {html(value)}</li>" for key, value in items
    )


def card(item):
    detail = f"pens/{url(item['slug'])}.html"
    image = item["images"][0] if item["images"] else "assets/default-pen.svg"
    return f'''<article class="card">
  <div class="card__visual">
    <img src="../{url(image)}" alt="{html(item['title'])} reference" loading="lazy">
    <a class="card__preview-trigger" href="{detail}">View Details &amp; 3D Preview</a>
  </div>
  <div class="card__body">
    <h2 class="card__title"><a class="brand-link" href="{detail}">{html(item['title'])}</a></h2>
    <p class="card__id">{html(item['id'])}</p>
    <p class="card__desc">{html(item['description'])}</p>
    <ul class="metrics">{metrics(item['parameters'], 6)}</ul>
  </div>
</article>'''


def detail_page(item):
    downloads = "".join(
        f'<a class="btn" href="../../{url(path)}" download>{ext.upper()}</a>'
        if path else f'<span class="btn btn--ghost" aria-disabled="true">{ext.upper()} not built</span>'
        for ext, path in item["downloads"].items()
    )
    images = item["images"] or ["assets/default-pen.svg"]
    gallery = "".join(
        f'<button class="gallery-item" type="button" data-image="../../{url(image)}">'
        f'<img src="../../{url(image)}" alt="{html(item["title"])} reference" loading="lazy"></button>'
        for image in images
    )
    stl = item["downloads"]["stl"]
    viewer_data = script_json({"stl": "../../" + url(stl) if stl else None})
    return header(item["title"], "../../", "../", "../../pens/" + url(item["slug"]) + ".html") + f'''
<main class="detail-container">
  <a class="back-link" href="../index.html">← Back to OpenSCAD gallery</a>
  <section class="preview__panel">
    <div class="preview__header"><div>
      <p class="preview__eyebrow">Interactive preview · OpenSCAD</p>
      <h2 class="preview__title">{html(item['title'])}</h2>
      <p class="preview__meta">{html(item['id'])}</p>
    </div></div>
    <div class="preview__layout">
      <div class="preview__viewer-shell">
        <div id="viewer" class="viewer" aria-label="Interactive 3D model"></div>
        <div id="viewer-status" class="viewer__status" aria-live="polite">Loading preview...</div>
        <div id="main-image" class="main-image-container" hidden>
          <img src="../../{url(images[0])}" alt="{html(item['title'])} reference">
        </div>
      </div>
      <aside class="preview__sidebar">
        <p class="preview__description">{html(item['description'])}</p>
        <h3>Downloads</h3><div class="downloads downloads--stack">{downloads}</div>
        <p class="download-note">Slice the STL for your printer. The SCAD download is self-contained and editable in OpenSCAD.</p>
        <h3>Parameters</h3><ul class="metrics metrics--stack">{metrics(item['parameters'])}</ul>
      </aside>
    </div>
    <h3>Gallery</h3><div class="gallery-grid">
      <button id="show-viewer" class="gallery-item gallery-item--viewer" type="button" {'disabled' if not stl else ''}>3D viewer</button>
      {gallery}
    </div>
  </section>
</main>
<footer class="site-footer"><span>Built from the same YAML configurations with OpenSCAD</span></footer>
<script type="application/json" id="preview-data">{viewer_data}</script>
<script src="../detail.js" type="module"></script>
</body></html>
'''


def main():
    items = sorted((entry(path, pen) for path, pen in configurations()), key=lambda i: i["slug"])
    slugs = [item["slug"] for item in items]
    if len(slugs) != len(set(slugs)):
        raise ValueError("OpenSCAD gallery slugs must be unique")
    pages = GALLERY_DIR / "pens"
    pages.mkdir(parents=True, exist_ok=True)
    # Remove generated detail pages for deleted CMS configurations.
    for path in pages.glob("*.html"):
        if path.stem not in slugs:
            path.unlink()
    for item in items:
        (pages / f"{item['slug']}.html").write_text(detail_page(item), encoding="utf-8")
    index = header("Gallery", "../", "./", "../index.html") + '''
<main class="main"><section class="grid" aria-label="OpenSCAD designs">'''
    index += "\n".join(card(item) for item in items)
    index += '''</section></main>
<footer class="site-footer"><span>Built from the same YAML configurations with OpenSCAD</span></footer>
</body></html>\n'''
    (GALLERY_DIR / "index.html").write_text(index, encoding="utf-8")
    (GALLERY_DIR / "data.json").write_text(json.dumps({"pens": items}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated OpenSCAD gallery: {len(items)} designs in {GALLERY_DIR}")


if __name__ == "__main__":
    main()
