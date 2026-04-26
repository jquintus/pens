import sys
import subprocess
import importlib.util
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

# Models directory for arbitrary models
MODELS_DIR = REPO_ROOT / "models"

# To disable PrusaSlicer integration, comment out the line below:
ENABLE_SLICING = True

def export_result(result, output_file: Path) -> None:
    cq.exporters.export(result, str(output_file))
    print(f"Built: {output_file}")

def slice_stl(stl_path: Path, config_name: str) -> None:
    if not ENABLE_SLICING:
        return
    
    ini_path = REPO_ROOT / "slicer_configs" / f"{config_name}.ini"
    if not ini_path.exists():
        print(f"Slicer config not found: {ini_path}")
        return

    output_gcode = stl_path.with_name(f"{stl_path.stem}_{config_name}.gcode")
    
    print(f"Slicing {stl_path.name} with {config_name}...")
    try:
        subprocess.run([
            "prusa-slicer",
            "--export-gcode",
            "--load", str(ini_path),
            "--output", str(output_gcode),
            str(stl_path)
        ], check=True, capture_output=True)
        print(f"Generated G-code: {output_gcode}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Slicing failed for {config_name}: {e}")

def build_pen(config_path: Path):
    from cad.engine import build as build_model
    config = load_config(config_path)
    # Validate pen config
    get_nose_cone(config)
    result = build_model(config)
    return result, config

def build_custom_model(config_path: Path):
    model_dir = config_path.parent
    module_path = model_dir / "model.py"
    
    if not module_path.exists():
        raise FileNotFoundError(f"model.py not found in {model_dir}")
        
    config = load_config(config_path)
    
    # Dynamic import of model.py
    spec = importlib.util.spec_from_file_location("custom_model", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, 'build'):
        raise AttributeError(f"{module_path} must have a 'build' function")
        
    result = module.build(config.get("model", {}))
    return result, config

def build_all_in_dir(directory: Path, build_func, pattern="*.yml"):
    configs = sorted(directory.glob(pattern)) + sorted(directory.glob(pattern.replace(".yml", ".yaml")))
    for path in configs:
        if path.name.startswith("."): continue
        
        try:
            print(f"Processing {path}...")
            result, config = build_func(path)
            stem = output_stem(path, config)
            
            step_file = OUTPUT_DIR / f"{stem}.step"
            stl_file = OUTPUT_DIR / f"{stem}.stl"
            
            export_result(result, step_file)
            export_result(result, stl_file)

            if ENABLE_SLICING:
                profiles = config.get("slicing_profiles", [])
                for profile in profiles:
                    slice_stl(stl_file, profile)
        except Exception as e:
            print(f"Failed to build {path}: {e}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build Pens
    if CONFIG_DIR.is_dir():
        print("--- Building Pens ---")
        build_all_in_dir(CONFIG_DIR, build_pen)

    # Build Custom Models
    if MODELS_DIR.is_dir():
        print("--- Building Custom Models ---")
        for subfolder in sorted(MODELS_DIR.iterdir()):
            if subfolder.is_dir():
                config_path = subfolder / "config.yml"
                if not config_path.exists():
                    config_path = subfolder / "config.yaml"
                
                if config_path.exists():
                    build_all_in_dir(subfolder, build_custom_model, pattern=config_path.name)

if __name__ == "__main__":
    main()
