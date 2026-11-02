"""The optional center connector remains a separate printable STEP part."""

import copy
from pathlib import Path
import sys
import tempfile
import unittest

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cad.engine import build
from config_utils import load_config
from build import build_pen


class CenterConnectorCadQueryTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "configurations" / "design-pilot-bxs-v5rt-mach-3.yml"
        self.config = load_config(self.path)
        self.config["openscad"]["center_connector"] = {
            "position_mm": 50,
            "width_mm": 3,
            "diameter_mm": 11.5,
            "insertion_length_mm": 3,
            "insertion_diameter_mm": 7.4,
            "bore_diameter_mm": 6.2,
        }

    def test_step_has_three_separate_solids_with_hollow_connector(self):
        result = build(self.config)
        self.assertEqual(len(result.solids().vals()), 3)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pen.step"
            cq.exporters.export(result, str(path))
            imported = cq.importers.importStep(str(path))
            self.assertEqual(len(imported.solids().vals()), 3)
        solid = copy.deepcopy(self.config)
        solid["openscad"]["center_connector"]["bore_diameter_mm"] = 0
        self.assertGreater(build(solid).val().Volume(), result.val().Volume())

    def test_without_connector_keeps_two_solids(self):
        self.assertEqual(len(build(load_config(self.path)).solids().vals()), 2)

    def test_build_path_rejects_invalid_connector_before_cad_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.yml"
            path.write_text(self.path.read_text().replace(
                "  end_cap:\n", "  center_connector:\n    position_mm: 50\n    width_mm: 3\n"
                "    diameter_mm: 11.5\n    insertion_length_mm: 3\n"
                "    insertion_diameter_mm: 7.4\n    bore_diameter_mm: 7\n"
                "  end_cap:\n"))
            with self.assertRaisesRegex(ValueError, "wall"):
                build_pen(path)


if __name__ == "__main__":
    unittest.main()
