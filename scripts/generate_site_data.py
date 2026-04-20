#!/usr/bin/env python3
"""Write site/data.json from configurations/ and existing build outputs."""

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
    load_config,
    output_stem,
)


def repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def collect_downloads(stem: str) -> dict:
    base = OUTPUT_DIR / stem
    out = {}
    for ext, key in ((".step", "step"), (".stl", "stl"), (".gcode", "gcode")):
        p = base.with_suffix(ext)
        out[key] = f"outputs/{p.name}" if p.is_file() else None
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
        return []
    urls = []
    for item in raw:
        if not item:
            continue
        if isinstance(item, dict) and "path" in item:
            item = item["path"]
        resolved = resolve_gallery_image_path(str(item))
        if resolved:
            urls.append(repo_relative(resolved))
    return urls


def main():
    entries = []
    configs = sorted(CONFIG_DIR.glob("*.yml")) + sorted(CONFIG_DIR.glob("*.yaml"))
    for path in configs:
        if path.name.startswith("."):
            continue
        config = load_config(path)
        stem = output_stem(path, config)
        cid = str(config.get("id") or path.stem)
        title = str(config.get("title") or cid.replace("_", " ").title())
        description = str(config.get("description") or "").strip()

        entries.append(
            {
                "id": cid,
                "slug": path.stem,
                "title": title,
                "description": description,
                "metrics": config.get("metrics") or {},
                "images": normalize_gallery_paths(config),
                "downloads": collect_downloads(stem),
            }
        )

    entries.sort(key=lambda e: e["slug"])

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    data_path = SITE_DIR / "data.json"
    data_path.write_text(json.dumps({"pens": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {data_path} ({len(entries)} pens)")


if __name__ == "__main__":
    main()
