"""The fit sweep produces one design with exact, matching CAD backend variants."""

from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config_utils import (fit_sweep_values, fit_variant_config, fit_variant_stem,
                          is_base_fit_variant, load_config, output_stem)
from build_openscad import build_all
from generate_openscad_site import detail_page, entry
from generate_site_data import process_config


class FitSweepTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "configurations" / "pilot_precise_v5rt_7_60.yml"
        self.config = load_config(self.path)
        self.config["fit_sweep"] = {
            "target": "nose_insertion_diameter_mm",
            "start_mm": 7.4,
            "end_mm": 7.45,
            "step_mm": 0.01,
        }

    def test_exact_inclusive_values_and_stable_safe_stems(self):
        values = fit_sweep_values(self.config)
        self.assertEqual(values, [Decimal("7.40"), Decimal("7.41"), Decimal("7.42"),
                                  Decimal("7.43"), Decimal("7.44"), Decimal("7.45")])
        self.assertIn("_fit_7p41_", fit_variant_stem(self.path, self.config, values[1]))
        self.assertEqual(output_stem(self.path, self.config), output_stem(self.path, load_config(self.path)))

    def test_rejects_ranges_that_cannot_include_endpoint(self):
        self.config["fit_sweep"]["step_mm"] = 0.02
        with self.assertRaisesRegex(ValueError, "land exactly"):
            fit_sweep_values(self.config)
        self.config["fit_sweep"]["step_mm"] = 0
        with self.assertRaisesRegex(ValueError, "positive step"):
            fit_sweep_values(self.config)

    def test_variant_copy_updates_both_backends_and_leaves_base_unchanged(self):
        original = load_config(self.path)
        self.config["openscad"] = {"nose_cone": {"insertion_diameter_mm": 7.6}}
        variant = fit_variant_config(self.config, Decimal("7.41"))
        self.assertEqual(variant["nose_cone"]["cylinder_outside_diameter"], 7.41)
        self.assertEqual(variant["openscad"]["nose_cone"]["insertion_diameter_mm"], 7.41)
        self.assertEqual(original["nose_cone"]["cylinder_outside_diameter"], 7.6)
        self.assertEqual(self.config["nose_cone"]["cylinder_outside_diameter"], 7.6)
        self.assertFalse(is_base_fit_variant(self.config, Decimal("7.41")))
        self.assertNotIn("openscad", fit_variant_config(original, Decimal("7.41")))

    def test_openscad_build_keeps_base_and_adds_each_fit(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            def render(command, **kwargs):
                Path(command[2]).write_bytes(b"stl")
                return mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch("config_utils.resolve_release_version", return_value="dev"), \
                 mock.patch("build_openscad.configurations", return_value=[(self.path, "pen")]), \
                 mock.patch("build_openscad.load_config", return_value=self.config), \
                 mock.patch("build_openscad.subprocess.run", side_effect=render):
                built = build_all("openscad", output)
                self.assertEqual(len(built), 7)
                self.assertTrue((output / (output_stem(self.path, self.config) + ".scad")).is_file())
                source = (output / (fit_variant_stem(self.path, self.config, Decimal("7.41")) + ".scad")).read_text()
                self.assertIn("cylinder_outside_diameter = 7.41;", source)

    def test_one_gallery_entry_groups_fit_downloads(self):
        with mock.patch("generate_site_data.load_config", return_value=self.config), \
             mock.patch("generate_openscad_site.load_config", return_value=self.config):
            cad = process_config(self.path)
            scad = entry(self.path, True)
        self.assertEqual(len(cad["fit_variants"]), 6)
        self.assertEqual(len(scad["fit_variants"]), 6)
        self.assertIn("7.41 mm insertion", detail_page(scad))
        self.assertEqual(cad["slug"], self.path.stem)
        self.assertEqual(scad["slug"], self.path.stem)

    def test_without_sweep_preserves_gallery_contract(self):
        config = load_config(self.path)
        self.assertEqual(fit_sweep_values(config), [])
        with mock.patch("generate_site_data.load_config", return_value=config), \
             mock.patch("generate_openscad_site.load_config", return_value=config):
            self.assertNotIn("fit_variants", process_config(self.path))
            self.assertNotIn("fit_variants", entry(self.path, True))


if __name__ == "__main__":
    unittest.main()
