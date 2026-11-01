"""Validate the refill catalog's tip-referenced axial measurements."""

import math
import re
from datetime import date
from pathlib import Path

from config_utils import REPO_ROOT, load_config

REFILL_DIR = REPO_ROOT / "refills"
STATUSES = {"measured", "approximate", "incomplete"}
FORMATS = {"unknown", "parker-g2", "pilot-g2", "d1", "euro", "proprietary", "other"}
INK_TYPES = {"unknown", "gel", "ballpoint", "rollerball", "hybrid", "fountain", "felt-tip", "other"}
TIP_SHAPES = {"unknown", "needle", "conical", "synergy", "ballpoint", "fineliner", "felt", "other"}
KINDS = {
    "cylinder": ("diameter_mm",),
    "taper": ("diameter_start_mm", "diameter_end_mm"),
}


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return float(value)


def validate_refill(refill):
    """Return a copy with derived length and geometry readiness.

    Unknown fields may be omitted only when the record or segment is marked
    incomplete. A known end distance always measures from the writing tip.
    """
    if not isinstance(refill, dict):
        raise ValueError("refill must be a mapping")
    result = dict(refill)
    slug = result.get("id")
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9_-]+", slug):
        raise ValueError("id must be a lowercase slug")
    for field in ("brand", "model", "format"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise ValueError(f"{field} is required")
    for field, choices in (("format", FORMATS), ("ink_type", INK_TYPES), ("tip_shape", TIP_SHAPES)):
        value = result.get(field)
        if value is not None and (not isinstance(value, str) or value not in choices):
            raise ValueError(f"{field} must be one of: {', '.join(sorted(choices))}")
    source_pens = result.get("source_pens")
    if source_pens is not None and (not isinstance(source_pens, list) or
                                    any(not isinstance(name, str) or not name.strip() for name in source_pens)):
        raise ValueError("source_pens must be a list of pen names")
    for field in ("pen_photos", "ink_photos", "photos"):
        value = result.get(field)
        if value is not None and (not isinstance(value, list) or
                                  any(not isinstance(path, str) or not path.strip() for path in value)):
            raise ValueError(f"{field} must be a list of image paths")
    status = result.get("measurement_status")
    if status not in STATUSES:
        raise ValueError("measurement_status must be measured, approximate, or incomplete")
    rating = result.get("rating")
    if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5):
        raise ValueError("rating must be an integer from 1 to 5")
    prices = result.get("prices", [])
    if not isinstance(prices, list):
        raise ValueError("prices must be a list")
    for index, price in enumerate(prices, 1):
        if not isinstance(price, dict):
            raise ValueError(f"price {index} must be a mapping")
        for field in ("source", "item", "url", "checked_on"):
            if not isinstance(price.get(field), str) or not price[field].strip():
                raise ValueError(f"price {index} {field} is required")
        if not re.fullmatch(r"https://[^\s]+", price["url"]):
            raise ValueError(f"price {index} url must use HTTPS")
        try:
            date.fromisoformat(price["checked_on"])
        except ValueError as error:
            raise ValueError(f"price {index} checked_on must be YYYY-MM-DD") from error
        _positive(price.get("amount_usd"), f"price {index} amount_usd")
    segments = result.get("segments")
    if not isinstance(segments, list) or (not segments and status != "incomplete"):
        raise ValueError("segments must be nonempty unless the refill is incomplete")
    known_end = 0.0
    complete = bool(segments)
    normalized = []
    for index, segment in enumerate(segments, 1):
        label = f"segment {index}"
        if not isinstance(segment, dict):
            raise ValueError(f"{label} must be a mapping")
        item = dict(segment)
        kind = item.get("kind")
        if kind not in KINDS:
            raise ValueError(f"{label} kind must be cylinder or taper")
        item_status = item.get("measurement_status", status)
        if item_status not in STATUSES:
            raise ValueError(f"{label} has invalid measurement_status")
        required = (*KINDS[kind], "end_distance_mm")
        for field in required:
            value = item.get(field)
            if value is None:
                if item_status != "incomplete" and status != "incomplete":
                    raise ValueError(f"{label} {field} is required unless marked incomplete")
                complete = False
            else:
                item[field] = _positive(value, f"{label} {field}")
        end = item.get("end_distance_mm")
        if end is not None:
            if end <= known_end:
                raise ValueError(f"{label} end_distance_mm must exceed earlier end distances")
            known_end = end
        if item_status == "incomplete":
            complete = False
        normalized.append(item)
    if status == "incomplete":
        complete = False
    result["segments"] = normalized
    result["overall_length_mm"] = normalized[-1].get("end_distance_mm") if complete else None
    result["geometry_ready"] = complete
    return result


def load_refills(directory=REFILL_DIR):
    """Load every catalog record and reject duplicate IDs or invalid geometry."""
    records = []
    seen = set()
    for path in sorted([*Path(directory).glob("*.yml"), *Path(directory).glob("*.yaml")]):
        if path.name.startswith("."):
            continue
        try:
            record = validate_refill(load_config(path))
        except (ValueError, KeyError) as error:
            raise ValueError(f"{path}: {error}") from error
        if record["id"] in seen:
            raise ValueError(f"duplicate refill ID: {record['id']}")
        seen.add(record["id"])
        records.append(record)
    return records
