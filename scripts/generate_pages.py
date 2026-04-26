#!/usr/bin/env python3
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = REPO_ROOT / "site"
DATA_PATH = SITE_DIR / "data.json"
TEMPLATE_PATH = SITE_DIR / "detail_template.html"
PENS_DIR = SITE_DIR / "pens"

def generate_pages():
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found. Run generate_site_data.py first.")
        return

    if not TEMPLATE_PATH.exists():
        print(f"Error: {TEMPLATE_PATH} not found.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    PENS_DIR.mkdir(parents=True, exist_ok=True)

    for pen in data["pens"]:
        slug = pen.get("actual_slug", pen["slug"])
        title = pen["title"]
        description = pen.get("description", "No description yet.")
        pen_id = pen["id"]
        
        # Downloads HTML
        downloads_html = ""
        d = pen.get("downloads", {})
        # Standard downloads
        for label, key in [("STEP", "step"), ("STL", "stl")]:
            path = d.get(key)
            if path:
                downloads_html += f'<a href="../{path}" class="btn" download>{label}</a>\n'
            else:
                downloads_html += f'<a href="#" class="btn btn--ghost" aria-disabled="true">{label}</a>\n'
        
        # G-code variants
        slicing_profiles = pen.get("slicing_profiles", [])
        for variant in slicing_profiles:
            key = f"gcode_{variant}"
            path = d.get(key)
            if path:
                label = f"G-code ({variant})"
                downloads_html += f'<a href="../{path}" class="btn" download>{label}</a>\n'

        # Metrics HTML
        metrics_html = ""
        nose_cone = pen.get("nose_cone", {})
        for k, v in nose_cone.items():
            key_label = k.replace("_", " ")
            metrics_html += f'<li>{key_label}: {v}</li>\n'

        # Gallery HTML
        gallery_html = ""
        images = pen.get("images", [])
        for img_path in images:
            gallery_html += f'''
            <div class="gallery-item" onclick="setMainImage('../{img_path}')">
                <img src="../{img_path}" alt="{title} reference">
            </div>
            '''

        # Fill template
        content = template
        content = content.replace("{{TITLE}}", title)
        content = content.replace("{{DESCRIPTION}}", description)
        content = content.replace("{{ID}}", pen_id)
        content = content.replace("{{SLUG}}", slug)
        content = content.replace("{{DOWNLOADS}}", downloads_html)
        content = content.replace("{{METRICS}}", metrics_html)
        content = content.replace("{{GALLERY}}", gallery_html)
        content = content.replace("{{STL_URL}}", d.get("stl") or "null")
        content = content.replace("{{IMAGE}}", images[0] if images else "assets/default-pen.svg")

        output_path = PENS_DIR / f"{slug}.html"
        output_path.write_text(content, encoding="utf-8")
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    generate_pages()
