"""Shared helpers for build and site generation."""

import os
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configurations"
OUTPUT_DIR = REPO_ROOT / "outputs"
SITE_DIR = REPO_ROOT / "site"
ASSETS_DIR = REPO_ROOT / "assets"


def load_config(path: Path) -> dict:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def normalize_version_for_filename(version: str) -> str:
    s = version.strip()
    if not s:
        return "dev"
    if s.startswith("v") and len(s) > 1:
        return "v" + s[1:].replace(".", "_")
    return s.replace(".", "_")


def resolve_release_version() -> str:
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
