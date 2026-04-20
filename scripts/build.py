import sys
from pathlib import Path

import cadquery as cq

from config_utils import (
    CONFIG_DIR,
    OUTPUT_DIR,
    REPO_ROOT,
    get_nose_cone,
    load_config,
    output_stem,
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cad.engine import build as build_model


def export_result(result, output_file: Path) -> None:
    cq.exporters.export(result, str(output_file))
    print(f"Built: {output_file}")


def build_one(config_path: Path) -> Path:
    config = load_config(config_path)
    get_nose_cone(config)

    result = build_model(config)
    stem = output_stem(config_path, config)
    step_file = OUTPUT_DIR / f"{stem}.step"
    stl_file = OUTPUT_DIR / f"{stem}.stl"
    export_result(result, step_file)
    export_result(result, stl_file)
    return step_file


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
