"""Shared helpers for build and site generation."""

import os
import re
import subprocess
from copy import deepcopy
from decimal import Decimal, InvalidOperation
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


def get_nose_cone(config: dict) -> dict:
    nose_cone = config.get("nose_cone")
    if not isinstance(nose_cone, dict):
        raise KeyError("missing required key 'nose_cone'")
    return nose_cone


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


def output_base_name(config_path: Path, config: dict) -> str:
    out = config.get("output") or {}
    base = out.get("name")
    if not base:
        base = config.get("id") or config_path.stem
    return str(base)


def output_stem(config_path: Path, config: dict) -> str:
    base = output_base_name(config_path, config)
    ver = normalize_version_for_filename(resolve_release_version())
    return f"{base}_{ver}"


def _fit_decimal(value, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"fit_sweep.{field} must be a finite number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"fit_sweep.{field} must be a finite number") from error
    if not result.is_finite():
        raise ValueError(f"fit_sweep.{field} must be a finite number")
    return result


def fit_sweep_values(config: dict) -> list[Decimal]:
    """Return inclusive, exact insertion diameters for an optional print-fit sweep."""
    raw = config.get("fit_sweep")
    if raw is None:
        return []
    if not isinstance(raw, dict) or set(raw) != {"target", "start_mm", "end_mm", "step_mm"}:
        raise ValueError("fit_sweep needs target, start_mm, end_mm, and step_mm")
    if raw["target"] != "nose_insertion_diameter_mm":
        raise ValueError("fit_sweep.target must be nose_insertion_diameter_mm")
    start, end, step = (_fit_decimal(raw[key], key) for key in ("start_mm", "end_mm", "step_mm"))
    if start <= 0 or end < start or step <= 0:
        raise ValueError("fit_sweep needs positive diameters, an increasing range, and a positive step")
    count = (end - start) / step
    if count != count.to_integral_value():
        raise ValueError("fit_sweep.step_mm must land exactly on end_mm")
    if count > 100:
        raise ValueError("fit_sweep may contain at most 101 diameters")
    return [start + index * step for index in range(int(count) + 1)]


def fit_variant_config(config: dict, diameter: Decimal) -> dict:
    """Update both CAD backends on an isolated copy of one design."""
    variant = deepcopy(config)
    get_nose_cone(variant)["cylinder_outside_diameter"] = float(diameter)
    # Legacy OpenSCAD profiles derive insertion diameter from nose_cone. Adding
    # an openscad block would switch their entire shape to designer_parts.
    if "openscad" in variant:
        variant["openscad"].setdefault("nose_cone", {})["insertion_diameter_mm"] = float(diameter)
    return variant


def fit_variant_stem(path: Path, config: dict, diameter: Decimal) -> str:
    """Place a filesystem-safe fit label before the release version."""
    sweep = config["fit_sweep"]
    precision = min(_fit_decimal(sweep["step_mm"], "step_mm").as_tuple().exponent, 0)
    label = format(diameter.quantize(Decimal(1).scaleb(precision)), "f").replace(".", "p")
    base = output_base_name(path, config)
    version = normalize_version_for_filename(resolve_release_version())
    return f"{base}_fit_{label}_{version}"


def is_base_fit_variant(config: dict, diameter: Decimal) -> bool:
    legacy = _fit_decimal(get_nose_cone(config)["cylinder_outside_diameter"], "base_diameter")
    openscad = config.get("openscad", {}).get("nose_cone", {}).get("insertion_diameter_mm", legacy)
    return legacy == diameter and _fit_decimal(openscad, "base_diameter") == diameter
