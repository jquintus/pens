"""Check print-critical geometry and CMS-to-gallery contracts through build outputs."""
import copy
import importlib.util
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlparse

import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from build_openscad import configurations, designer_parameters, parameters, source_text
from config_utils import load_config, output_stem
from generate_openscad_site import detail_page


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.paths.append(value)


class OpenSCADBuildTests(unittest.TestCase):
    def test_all_configurations_are_closed_printable_solids(self):
        entries = list(configurations())
        self.assertGreater(len(entries), 0)
        for path, kind in entries:
            with self.subTest(path=path.name):
                config = load_config(path)
                artifact = ROOT / 'outputs' / 'openscad' / (output_stem(path, config) + '.stl')
                mesh = trimesh.load(artifact, force='mesh')
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(mesh.volume, 0)
                components = mesh.split(only_watertight=False)
                self.assertEqual(len(components), 2 if kind == 'pen' else 1)
                values = parameters(config, kind)
                if kind == 'pen' and 'openscad' in config:
                    design = designer_parameters(config)
                    expected_height = max(
                        design['nose_cone']['visible_length_mm'] + design['nose_cone']['insertion_length_mm'],
                        design['end_cap']['length_mm'] + design['end_cap']['insertion_length_mm'])
                else:
                    expected_height = (values['cylinder_height'] + values['frustum_height'] if kind == 'pen'
                                       else values['back_height_in'] * 25.4)
                self.assertAlmostEqual(mesh.extents[2], expected_height, delta=0.015)
                if kind == 'c_bracket':
                    self.assertAlmostEqual(mesh.extents[0], values['width_in'] * 25.4, delta=0.015)
                    self.assertAlmostEqual(mesh.extents[1], values['length_in'] * 25.4, delta=0.015)

    def test_mesh_matches_cadquery_dimensions_and_rounded_volume(self):
        from cad.engine import build
        for path, kind in configurations():
            with self.subTest(path=path.name):
                config = load_config(path)
                if kind == 'pen' and 'openscad' in config:
                    continue  # CAD-specific dimensions intentionally differ from CadQuery.
                if kind == 'pen':
                    original = build(config)
                else:
                    spec = importlib.util.spec_from_file_location('original_bracket', path.parent / 'model.py')
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    original = module.build(config.get('model', {}))
                solid = original.val()
                bounds = solid.BoundingBox()
                expected = [bounds.xlen, bounds.ylen, bounds.zlen]
                mesh = trimesh.load(ROOT / 'outputs/openscad' / (output_stem(path, config) + '.stl'), force='mesh')
                for actual, dimension in zip(mesh.extents, expected):
                    self.assertAlmostEqual(actual, dimension, delta=0.015)
                self.assertLess(abs(mesh.volume - solid.Volume()) / solid.Volume(), 0.002)

    def test_portable_sources_and_downloads_match_every_config(self):
        data = json.loads((ROOT / 'site/openscad/data.json').read_text())['pens']
        self.assertEqual(len(data), len(list(configurations())))
        for item in data:
            self.assertEqual(set(item['downloads']), {'stl', 'scad'})
            for extension, path in item['downloads'].items():
                self.assertIsNotNone(path)
                self.assertTrue((ROOT / path).is_file())
                if extension == 'scad':
                    text = (ROOT / path).read_text()
                    self.assertNotIn('include <', text)
                    self.assertNotIn('use <', text)

    def test_gallery_local_resources_resolve_under_published_layout(self):
        # Published site puts assets/ and outputs/ next to the site content.
        for page in (ROOT / 'site/openscad').rglob('*.html'):
            parser = Links()
            parser.feed(page.read_text())
            for link in parser.paths:
                parsed = urlparse(link)
                if parsed.scheme or link.startswith('#'):
                    continue
                target = (page.parent / unquote(parsed.path)).resolve()
                # CadQuery counterparts are generated by the existing deploy pipeline.
                if target.parent == ROOT / 'site/pens':
                    expected = {p.stem if kind == 'pen' else p.parent.name for p, kind in configurations()}
                    self.assertIn(target.stem, expected)
                    continue
                if not target.exists() and target.is_relative_to(ROOT / 'site'):
                    target = ROOT / target.relative_to(ROOT / 'site')
                self.assertTrue(target.exists(), f'{page.name}: {link}')

    def test_invalid_dimensions_cannot_produce_a_download(self):
        path, kind = next(configurations())
        config = load_config(path)
        for key, value in [('cylinder_height', -1), ('top_hole_height', 999),
                           ('top_hole_diameter', float('nan')), ('frustum_height', True)]:
            bad = copy.deepcopy(config)
            bad['nose_cone'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                source_text(bad, kind)
        with self.assertRaises(ValueError):
            source_text({'model': {}}, 'unknown_model')

    def test_designer_dimensions_are_independent_and_validated(self):
        path, _ = next(configurations())
        config = load_config(path)
        legacy = source_text(config, 'pen')
        config['openscad'] = {'nose_cone': {'visible_length_mm': 15},
                              'end_cap': {'length_mm': 4}}
        source = source_text(config, 'pen')
        self.assertIn('designer_parts(', source)
        self.assertIn('nose_cone_visible_length_mm = 15.0;', source)
        self.assertIn('end_cap_length_mm = 4.0;', source)
        self.assertNotIn('include <', source)
        self.assertEqual(parameters(config, 'pen'), parameters(load_config(path), 'pen'))
        self.assertNotEqual(legacy, source)
        for section, key, value in (
            ('nose_cone', 'passage_diameter_mm', 50),
            ('nose_cone', 'stop_depth_mm', 100),
            ('nose_cone', 'round_radius_mm', 100),
            ('end_cap', 'insertion_diameter_mm', 50),
        ):
            bad = copy.deepcopy(config)
            bad['openscad'][section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                source_text(bad, 'pen')

    def test_designer_prints_two_closed_solids(self):
        executable = shutil.which('openscad')
        if not executable:
            self.skipTest('OpenSCAD is not installed')
        path, _ = next(configurations())
        config = load_config(path)
        total = 15 + config['nose_cone']['cylinder_height']
        config['openscad'] = {'nose_cone': {'visible_length_mm': 15,
                                           'bore_segments': [
                                               {'kind': 'cylinder', 'diameter_mm': 2.5,
                                                'end_distance_mm': 4},
                                               {'kind': 'taper', 'diameter_start_mm': 2.5,
                                                'diameter_end_mm': 4.2, 'end_distance_mm': 9},
                                               {'kind': 'cylinder', 'diameter_mm': 4.2,
                                               'end_distance_mm': total},
                                           ]},
                              'end_cap': {'length_mm': 4}}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'designer.scad'
            stl = Path(folder) / 'designer.stl'
            source.write_text(source_text(config, 'pen'))
            process = subprocess.run([executable, '-o', str(stl), str(source)],
                                     capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            mesh = trimesh.load(stl, force='mesh')
            self.assertTrue(mesh.is_watertight)
            self.assertEqual(len(mesh.split(only_watertight=False)), 2)
            self.assertAlmostEqual(mesh.extents[2], total, delta=0.02)

    def test_optional_center_connector_prints_as_third_part(self):
        executable = shutil.which('openscad')
        if not executable:
            self.skipTest('OpenSCAD is not installed')
        config = load_config(ROOT / 'configurations' / 'design-pilot-bxs-v5rt-mach-3.yml')
        config['openscad']['center_connector'] = {
            'position_mm': 50, 'width_mm': 3, 'diameter_mm': 10.795,
            'insertion_length_mm': 3, 'insertion_diameter_mm': 7.4,
            'bore_diameter_mm': 6.2,
        }
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'connector.scad'
            stl = Path(folder) / 'connector.stl'
            for bore in (6.2, 0):
                with self.subTest(bore=bore):
                    config['openscad']['center_connector']['bore_diameter_mm'] = bore
                    source.write_text(source_text(config, 'pen'))
                    process = subprocess.run([executable, '-o', str(stl), str(source)],
                                             capture_output=True, text=True)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    mesh = trimesh.load(stl, force='mesh')
                    self.assertTrue(mesh.is_watertight)
                    self.assertEqual(len(mesh.split(only_watertight=False)), 3)

    def test_center_connector_rejects_unprintable_or_overlapping_dimensions(self):
        config = load_config(ROOT / 'configurations' / 'design-pilot-bxs-v5rt-mach-3.yml')
        config['openscad']['center_connector'] = {
            'position_mm': 50, 'width_mm': 3, 'diameter_mm': 10.795,
            'insertion_length_mm': 3, 'insertion_diameter_mm': 7.4,
            'bore_diameter_mm': 6.2,
        }
        self.assertIn('center_connector_enabled = true;', source_text(config, 'pen'))
        for key, value in [('position_mm', 5), ('width_mm', 100),
                           ('diameter_mm', 7), ('diameter_mm', 10.8), ('insertion_diameter_mm', 8),
                           ('bore_diameter_mm', 7), ('width_mm', float('nan'))]:
            bad = copy.deepcopy(config)
            bad['openscad']['center_connector'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                designer_parameters(bad)
        bad = copy.deepcopy(config)
        bad['barrel']['bushing_id'] = 'PKCP2400BU'
        with self.assertRaisesRegex(ValueError, 'three-piece bushing'):
            designer_parameters(bad)

    def test_segmented_bore_uses_tip_referenced_ends(self):
        path, _ = next(configurations())
        config = load_config(path)
        total = config['nose_cone']['frustum_height'] + config['nose_cone']['cylinder_height']
        config['openscad'] = {'nose_cone': {'bore_segments': [
            {'kind': 'cylinder', 'diameter_mm': 2.5, 'end_distance_mm': 4},
            {'kind': 'taper', 'diameter_start_mm': 2.5,
             'diameter_end_mm': 4.2, 'end_distance_mm': 9},
            {'kind': 'cylinder', 'diameter_mm': 4.2, 'end_distance_mm': total},
        ]}}
        normalized = designer_parameters(config)['nose_cone']['bore_segments']
        self.assertEqual(normalized, [[2.5, 2.5, 4], [2.5, 4.2, 9], [4.2, 4.2, total]])
        self.assertIn('nose_cone_bore_segments = [[2.5, 2.5, 4.0],', source_text(config, 'pen'))
        for edit in (
            lambda parts: parts[1].update(end_distance_mm=3),
            lambda parts: parts[2].update(end_distance_mm=15),
            lambda parts: parts[0].update(diameter_mm=5),
            lambda parts: parts[1].update(diameter_end_mm=float('nan')),
        ):
            bad = copy.deepcopy(config)
            edit(bad['openscad']['nose_cone']['bore_segments'])
            with self.assertRaises(ValueError):
                designer_parameters(bad)

    def test_config_text_is_not_interpreted_as_page_markup(self):
        item = {'slug': 'example', 'id': 'example', 'title': '<script>alert(1)</script>',
                'description': '<img src=x onerror=alert(1)>', 'parameters': {},
                'images': [], 'downloads': {'stl': None, 'scad': None}}
        page = detail_page(item)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertNotIn('<img src=x onerror', page)
        self.assertIn('&lt;script&gt;', page)


if __name__ == '__main__':
    unittest.main()
