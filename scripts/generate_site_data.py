#!/usr/bin/env python3
"""Write site/data.json from configurations/, models/ and existing build outputs."""

import json
import sys
from pathlib import Path

# Allow running as `python scripts/generate_site_data.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_utils import (
    ASSETS_DIR,
    CONFIG_DIR,
    OUTPUT_DIR,
    REPO_ROOT,
    SITE_DIR,
    get_nose_cone,
    load_config,
    output_base_name,
    output_stem,
)

DEFAULT_IMAGE = ASSETS_DIR / "default-pen.svg"
MODELS_DIR = REPO_ROOT / "models"

def repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()

def resolve_output_path(base_name: str, stem: str, ext: str) -> Path | None:
    exact = (OUTPUT_DIR / stem).with_suffix(ext)
    if exact.is_file():
        return exact

    matches = sorted(OUTPUT_DIR.glob(f"{base_name}_*{ext}"))
    if matches:
        return matches[-1]

    legacy = (OUTPUT_DIR / base_name).with_suffix(ext)
    if legacy.is_file():
        return legacy

    return None

def collect_downloads(base_name: str, stem: str) -> dict:
    out = {}
    for ext, key in ((".step", "step"), (".stl", "stl")):
        p = resolve_output_path(base_name, stem, ext)
        out[key] = f"outputs/{p.name}" if p else None
    
    # Handle G-code variants
    for variant in ["fast", "quality"]:
        p = resolve_output_path(base_name, f"{stem}_{variant}", ".gcode")
        out[f"gcode_{variant}"] = f"outputs/{p.name}" if p else None
        
    return out

def resolve_gallery_image_path(raw: str) -> Path | None:
    """Resolve CMS paths (often under assets/) or repo-relative paths."""
    s = str(raw).strip().lstrip("/")
    if not s:
        return None
    candidates = [
        REPO_ROOT / s,
        ASSETS_DIR / s,
        REPO_ROOT / "assets" / s,
    ]
    for p in candidates:
        try:
            pr = p.resolve()
            pr.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if pr.is_file():
            return pr
    return None

def normalize_gallery_paths(config: dict) -> list[str]:
    raw = config.get("gallery") or []
    if not isinstance(raw, list):
        raw = []
    urls = []
    for item in raw:
        if not item:
            continue
        if isinstance(item, dict) and "path" in item:
            item = item["path"]
        resolved = resolve_gallery_image_path(str(item))
        if resolved:
            urls.append(repo_relative(resolved))
    if not urls and DEFAULT_IMAGE.is_file():
        urls.append(repo_relative(DEFAULT_IMAGE))
    return urls

def process_config(path: Path, is_pen=True):
    config = load_config(path)
    base_name = output_base_name(path, config)
    stem = output_stem(path, config)
    cid = str(config.get("id") or path.stem)
    title = str(config.get("title") or cid.replace("_", " ").title())
    description = str(config.get("description") or "").strip()

    if is_pen:
        params = get_nose_cone(config)
    else:
        params = config.get("model", {})

    return {
        "id": cid,
        "slug": path.stem if is_pen else f"{path.parent.name}_{path.stem}",
        "actual_slug": path.stem if is_pen else path.parent.name,
        "title": title,
        "description": description,
        "nose_cone": params, # we keep the key for compatibility with detail_template.html
        "images": normalize_gallery_paths(config),
        "downloads": collect_downloads(base_name, stem),
    }

def main():
    entries = []
    
    # Pens
    if CONFIG_DIR.is_dir():
        configs = sorted(CONFIG_DIR.glob("*.yml")) + sorted(CONFIG_DIR.glob("*.yaml"))
        for path in configs:
            if path.name.startswith("."): continue
            entries.append(process_config(path, is_pen=True))

    # Custom Models
    if MODELS_DIR.is_dir():
        for subfolder in sorted(MODELS_DIR.iterdir()):
            if subfolder.is_dir():
                config_path = subfolder / "config.yml"
                if not config_path.exists():
                    config_path = subfolder / "config.yaml"
                
                if config_path.exists():
                    entries.append(process_config(config_path, is_pen=False))

    entries.sort(key=lambda e: e["slug"])

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    data_path = SITE_DIR / "data.json"
    data_path.write_text(json.dumps({"pens": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {data_path} ({len(entries)} items)")

if __name__ == "__main__":
    main()
