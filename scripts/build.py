import sys
from pathlib import Path

import cadquery as cq

from config_utils import (
    CONFIG_DIR,
    OUTPUT_DIR,
    REPO_ROOT,
    load_config,
    output_stem,
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cad.engine import build as build_model


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
