#!/usr/bin/env python3
"""Build self-contained OpenSCAD sources and STL files from the existing CMS YAML."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from config_utils import CONFIG_DIR, REPO_ROOT, load_config, output_stem

OUTPUT_DIR = REPO_ROOT / 'outputs' / 'openscad'
PEN_KEYS = ('cylinder_height', 'cylinder_outside_diameter', 'frustum_height',
            'frustum_top_diameter', 'frustum_bottom_diameter', 'top_hole_diameter',
            'bottom_hole_diameter', 'top_hole_height')
BRACKET_DEFAULTS = dict(width_in=0.5, thickness_in=0.125, length_in=1.0,
                        back_height_in=2.0, lip_height_in=0.5)


def configurations():
    for path in sorted([*CONFIG_DIR.glob('*.yml'), *CONFIG_DIR.glob('*.yaml')]):
        if not path.name.startswith('.'):
            yield path, 'pen'
    for folder in sorted((REPO_ROOT / 'models').iterdir()):
        if folder.is_dir():
            for name in ('config.yml', 'config.yaml'):
                path = folder / name
                if path.is_file():
                    yield path, folder.name
                    break


def parameters(config, kind):
    if kind == 'pen':
        raw = config.get('nose_cone')
        if not isinstance(raw, dict):
            raise ValueError('nose_cone must be a mapping')
        values = {key: raw[key] for key in PEN_KEYS}
    elif kind == 'c_bracket':
        raw = config.get('model', {})
        if not isinstance(raw, dict):
            raise ValueError('model must be a mapping')
        values = {key: raw.get(key, default) for key, default in BRACKET_DEFAULTS.items()}
    else:
        raise ValueError(f'No OpenSCAD implementation for model {kind!r}')
    result = {}
    for key, value in values.items():
        if isinstance(value, bool):
            raise ValueError(f'{key} must be numeric')
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f'{key} must be finite')
        if value < 0 or (value == 0 and key not in ('frustum_height', 'top_hole_height')):
            raise ValueError(f'{key} must be positive')
        result[key] = value
    if kind == 'pen':
        height = result['cylinder_height'] + result['frustum_height']
        if result['top_hole_height'] > height:
            raise ValueError('top_hole_height exceeds total height')
        if result['bottom_hole_diameter'] >= min(result['cylinder_outside_diameter'], result['frustum_bottom_diameter']):
            raise ValueError('bottom bore must fit inside the nose cone')
        if result['top_hole_diameter'] >= result['frustum_top_diameter']:
            raise ValueError('top bore must fit inside the nose cone')
    return result


def source_text(config, kind):
    values = parameters(config, kind)
    source = REPO_ROOT / ('cad/openscad/pen_parts.scad' if kind == 'pen' else f'models/{kind}/model.scad')
    # Sources contain geometry modules; the generated file owns editable parameters.
    assignments = '\n'.join(f'{key} = {json.dumps(value)};' for key, value in values.items())
    module = 'pen_parts' if kind == 'pen' else 'c_bracket'
    arguments = ', '.join(f'{key}={key}' for key in values)
    return '// Generated from the shared Pages CMS YAML. Dimensions retain original units.\n' + assignments + '\n$fn = 128;\n\n' + source.read_text() + f'\n{module}({arguments});\n'


def build_all(executable, output_dir=OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    seen = set()
    built = []
    # Validate every config before rendering; fail CI rather than publishing a partial gallery.
    entries = []
    for path, kind in configurations():
        config = load_config(path)
        stem = output_stem(path, config)
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', stem):
            raise ValueError(f'Unsafe output name: {stem!r}')
        if stem in seen:
            raise ValueError(f'Duplicate output name: {stem}')
        seen.add(stem)
        entries.append((stem, source_text(config, kind)))
    for stem, text in entries:
        source = output_dir / f'{stem}.scad'
        stl = output_dir / f'{stem}.stl'
        source.write_text(text)
        # No modern-only flags: Ubuntu's packaged OpenSCAD supports this invocation.
        process = subprocess.run([executable, '-o', str(stl), str(source)],
                                 capture_output=True, text=True)
        if process.returncode or not stl.is_file() or stl.stat().st_size == 0 or re.search(r'^(WARNING|ERROR):', process.stderr, re.M):
            raise RuntimeError(f'OpenSCAD failed for {stem}:\n{process.stdout}\n{process.stderr}')
        print(f'Built OpenSCAD: {stl}', flush=True)
        built.append(stl)
    return built


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--openscad', default=os.environ.get('OPENSCAD') or shutil.which('openscad') or '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD')
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    try:
        build_all(args.openscad, args.output_dir)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
