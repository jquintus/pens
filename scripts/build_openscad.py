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

from config_utils import (CONFIG_DIR, REPO_ROOT, is_base_fit_variant, fit_sweep_values,
                          fit_variant_config, fit_variant_stem, load_config, output_stem)

OUTPUT_DIR = REPO_ROOT / 'outputs' / 'openscad'
PEN_KEYS = ('cylinder_height', 'cylinder_outside_diameter', 'frustum_height',
            'frustum_top_diameter', 'frustum_bottom_diameter', 'top_hole_diameter',
            'bottom_hole_diameter', 'top_hole_height')
BRACKET_DEFAULTS = dict(width_in=0.5, thickness_in=0.125, length_in=1.0,
                        back_height_in=2.0, lip_height_in=0.5)
DESIGNER_NOSE_KEYS = ('visible_length_mm', 'insertion_length_mm', 'insertion_diameter_mm',
                      'base_diameter_mm', 'tip_diameter_mm', 'passage_diameter_mm',
                      'stop_diameter_mm', 'stop_depth_mm', 'round_radius_mm')
DESIGNER_CAP_KEYS = ('length_mm', 'diameter_mm', 'tip_diameter_mm',
                     'insertion_length_mm', 'insertion_diameter_mm', 'round_radius_mm')


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


def designer_parameters(config):
    """Validate OpenSCAD-only dimensions without changing the CadQuery contract."""
    legacy = parameters(config, 'pen')
    raw = config.get('openscad')
    if not isinstance(raw, dict):
        raise ValueError('openscad must be a mapping')
    defaults = {
        'nose_cone': {
            'visible_length_mm': legacy['frustum_height'],
            'insertion_length_mm': legacy['cylinder_height'],
            'insertion_diameter_mm': legacy['cylinder_outside_diameter'],
            'base_diameter_mm': legacy['frustum_bottom_diameter'],
            'tip_diameter_mm': legacy['frustum_top_diameter'],
            'passage_diameter_mm': legacy['bottom_hole_diameter'],
            'stop_diameter_mm': legacy['top_hole_diameter'],
            'stop_depth_mm': legacy['top_hole_height'],
            'round_radius_mm': 0.4,
        },
        'end_cap': {
            'length_mm': 2.0,
            'diameter_mm': legacy['frustum_bottom_diameter'],
            'tip_diameter_mm': legacy['cylinder_outside_diameter'],
            'insertion_length_mm': legacy['cylinder_height'],
            'insertion_diameter_mm': legacy['cylinder_outside_diameter'],
            'round_radius_mm': 0.4,
        },
    }
    result = {}
    for section, keys in (('nose_cone', DESIGNER_NOSE_KEYS), ('end_cap', DESIGNER_CAP_KEYS)):
        supplied = raw.get(section, {})
        if not isinstance(supplied, dict):
            raise ValueError(f'openscad.{section} must be a mapping')
        allowed = set(keys) | ({'bore_segments'} if section == 'nose_cone' else set())
        unknown = set(supplied) - allowed
        if unknown:
            raise ValueError(f'Unknown openscad.{section} fields: {sorted(unknown)}')
        result[section] = {}
        for key in keys:
            value = supplied.get(key, defaults[section][key])
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f'openscad.{section}.{key} must be numeric')
            value = float(value)
            if not math.isfinite(value) or value < 0 or (value == 0 and key != 'round_radius_mm'):
                raise ValueError(f'openscad.{section}.{key} must be positive and finite')
            result[section][key] = value
    nose, cap = result['nose_cone'], result['end_cap']
    bore_segments = raw.get('nose_cone', {}).get('bore_segments')
    if bore_segments is not None:
        if not isinstance(bore_segments, list) or not bore_segments:
            raise ValueError('openscad.nose_cone.bore_segments must be a nonempty list')
        normalized = []
        previous_end = 0.0
        for index, segment in enumerate(bore_segments):
            if not isinstance(segment, dict):
                raise ValueError(f'Bore segment {index + 1} must be a mapping')
            kind = segment.get('kind')
            keys = ({'kind', 'diameter_mm', 'end_distance_mm'} if kind == 'cylinder'
                    else {'kind', 'diameter_start_mm', 'diameter_end_mm', 'end_distance_mm'}
                    if kind == 'taper' else set())
            if not keys or set(segment) != keys:
                raise ValueError(f'Bore segment {index + 1} must specify a cylinder or taper and its end distance')
            def dimension(key):
                value = segment[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f'Bore segment {index + 1} {key} must be numeric')
                value = float(value)
                if not math.isfinite(value) or value <= 0:
                    raise ValueError(f'Bore segment {index + 1} {key} must be positive and finite')
                return value
            end = dimension('end_distance_mm')
            if end <= previous_end:
                raise ValueError('Bore end distances must increase from the tip')
            first = dimension('diameter_mm' if kind == 'cylinder' else 'diameter_start_mm')
            last = first if kind == 'cylinder' else dimension('diameter_end_mm')
            normalized.append([first, last, end])
            previous_end = end
        total = nose['visible_length_mm'] + nose['insertion_length_mm']
        if not math.isclose(previous_end, total, abs_tol=1e-6, rel_tol=0):
            raise ValueError('Final bore end distance must equal total nose cone length')
        start = 0.0
        for first, last, end in normalized:
            positions = [start, end]
            if start < nose['visible_length_mm'] < end:
                positions.append(nose['visible_length_mm'])
            for position in positions:
                fraction = (position - start) / (end - start)
                bore = first + (last - first) * fraction
                outer = (nose['tip_diameter_mm'] +
                         (nose['base_diameter_mm'] - nose['tip_diameter_mm']) *
                         min(position, nose['visible_length_mm']) / nose['visible_length_mm'])
                if position >= nose['visible_length_mm']:
                    outer = min(outer, nose['insertion_diameter_mm'])
                if bore >= outer:
                    raise ValueError('Bore must fit within the nose cone at every segment boundary')
            start = end
        nose['bore_segments'] = normalized
    else:
        if nose['stop_depth_mm'] >= nose['visible_length_mm'] + nose['insertion_length_mm']:
            raise ValueError('Nose stop depth must be shorter than the nose cone')
        if nose['stop_diameter_mm'] >= nose['passage_diameter_mm']:
            raise ValueError('Nose stop diameter must be smaller than passage diameter')
        if nose['passage_diameter_mm'] >= min(nose['base_diameter_mm'], nose['insertion_diameter_mm']):
            raise ValueError('Nose passage must fit within the base and insertion')
        if nose['stop_diameter_mm'] >= nose['tip_diameter_mm']:
            raise ValueError('Nose stop bore must fit within the tip')
    if nose['insertion_diameter_mm'] >= nose['base_diameter_mm']:
        raise ValueError('Nose insertion must be narrower than the base')
    if cap['insertion_diameter_mm'] >= cap['diameter_mm']:
        raise ValueError('Cap insertion must be narrower than the outside diameter')
    for section, dimensions in result.items():
        if dimensions['round_radius_mm'] >= min(
            dimensions['tip_diameter_mm'] / 4,
            dimensions['insertion_length_mm'] / 2,
            dimensions['visible_length_mm' if section == 'nose_cone' else 'length_mm'] / 2,
        ):
            raise ValueError(f'{section} round radius is too large for the profile')
    return result


def source_text(config, kind):
    values = parameters(config, kind)
    source = REPO_ROOT / ('cad/openscad/pen_parts.scad' if kind == 'pen' else f'models/{kind}/model.scad')
    if kind == 'pen' and 'openscad' in config:
        design = designer_parameters(config)
        flat = {f'{section}_{key}': value for section, fields in design.items()
                for key, value in fields.items()}
        assignments = '\n'.join(f'{key} = {json.dumps(value)};' for key, value in flat.items())
        arguments = ', '.join(f'{key}={key}' for key in flat)
        return ('// Generated from the shared Pages CMS YAML. Dimensions are millimeters.\n'
                + assignments + '\n$fn = 128;\n\n' + source.read_text()
                + f'\ndesigner_parts({arguments});\n')
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
        variants = [(output_stem(path, config), config)]
        if kind == 'pen':
            diameters = fit_sweep_values(config)
            variants.extend((fit_variant_stem(path, config, diameter), fit_variant_config(config, diameter))
                            for diameter in diameters if not is_base_fit_variant(config, diameter))
        for stem, variant in variants:
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', stem):
                raise ValueError(f'Unsafe output name: {stem!r}')
            if stem in seen:
                raise ValueError(f'Duplicate output name: {stem}')
            seen.add(stem)
            entries.append((stem, source_text(variant, kind)))
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
