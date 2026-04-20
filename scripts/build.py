import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
import cadquery as cq

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configurations"
OUTPUT_DIR = REPO_ROOT / "outputs"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cad.engine import build as build_model


def load_config(path: Path) -> dict:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def normalize_version_for_filename(version: str) -> str:
    """Turn v1.0.8 or 1.0.8 into v1_0_8 / 1_0_8 for safe filenames."""
    s = version.strip()
    if not s:
        return "dev"
    if s.startswith("v") and len(s) > 1:
        return "v" + s[1:].replace(".", "_")
    return s.replace(".", "_")


def resolve_release_version() -> str:
    """Version label for output filenames; prefer CI (release tag), then git, else dev."""
    explicit = os.environ.get("PENS_RELEASE_VERSION", "").strip()
    if explicit:
        return explicit

    ref = os.environ.get("GITHUB_REF_NAME", "").strip()
    if ref and re.match(r"^v\d", ref):
        return ref

    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if tag:
            return tag
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return "dev"


def output_stem(config_path: Path, config: dict) -> str:
    out = config.get("output") or {}
    base = out.get("name")
    if not base:
        base = config_path.stem
    base = str(base)
    ver = normalize_version_for_filename(resolve_release_version())
    return f"{base}_{ver}"


def build_one(config_path: Path) -> Path:
    config = load_config(config_path)
    if "metrics" not in config:
        raise KeyError(f"{config_path}: missing required key 'metrics'")

    result = build_model(config)
    stem = output_stem(config_path, config)
    output_file = OUTPUT_DIR / f"{stem}.step"
    cq.exporters.export(result, str(output_file))
    print(f"Built: {output_file}")
    return output_file


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_DIR.is_dir():
        raise FileNotFoundError(
            f"Configuration directory not found: {CONFIG_DIR}\n"
            "Add one or more *.yml files under configurations/."
        )

    configs = sorted(CONFIG_DIR.glob("*.yml")) + sorted(CONFIG_DIR.glob("*.yaml"))
    if not configs:
        raise FileNotFoundError(
            f"No *.yml or *.yaml files in {CONFIG_DIR}\n"
            "Add configuration files to generate STEP outputs."
        )

    for path in configs:
        build_one(path)


if __name__ == "__main__":
    main()
