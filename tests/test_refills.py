"""Refill schema tests, including tip-referenced cumulative distances."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from refill_utils import load_refills, validate_refill


class RefillTests(unittest.TestCase):
    def record(self):
        return {
            "id": "test-refill", "brand": "Example", "model": "Test",
            "format": "Example", "measurement_status": "measured",
            "segments": [
                {"kind": "taper", "diameter_start_mm": 1, "diameter_end_mm": 2,
                 "end_distance_mm": 4},
                {"kind": "cylinder", "diameter_mm": 2, "end_distance_mm": 11},
            ],
        }

    def test_tip_referenced_ends_define_overall_length(self):
        result = validate_refill(self.record())
        self.assertTrue(result["geometry_ready"])
        self.assertEqual(result["overall_length_mm"], 11)

    def test_ends_must_increase(self):
        record = self.record()
        record["segments"][1]["end_distance_mm"] = 4
        with self.assertRaisesRegex(ValueError, "exceed"):
            validate_refill(record)

    def test_unknown_dimension_requires_incomplete_status(self):
        record = self.record()
        del record["segments"][0]["diameter_start_mm"]
        with self.assertRaisesRegex(ValueError, "required unless marked incomplete"):
            validate_refill(record)
        record["segments"][0]["measurement_status"] = "incomplete"
        result = validate_refill(record)
        self.assertFalse(result["geometry_ready"])
        self.assertIsNone(result["overall_length_mm"])

    def test_rejects_invalid_numbers(self):
        for invalid in (-1, 0, float("nan"), float("inf"), True, "5"):
            with self.subTest(invalid=invalid):
                record = self.record()
                record["segments"][0]["end_distance_mm"] = invalid
                with self.assertRaises(ValueError):
                    validate_refill(record)

    def test_catalog_fixture_is_explicit_example(self):
        records = load_refills()
        self.assertGreaterEqual(len(records), 1)
        examples = [record for record in records if record["id"] == "example-refill"]
        self.assertEqual(len(examples), 1)
        self.assertTrue(examples[0]["geometry_ready"])
        self.assertIn("Illustrative", examples[0]["measurement_notes"])

    def test_tg31880_uses_tip_referenced_measurements(self):
        record = next(r for r in load_refills() if r["id"] == "tian-zhuo-hoshi-tg31880")
        self.assertEqual(record["overall_length_mm"], 130)
        self.assertEqual([s["end_distance_mm"] for s in record["segments"]],
                         [3, 7.5, 14.2, 15.5, 130])
        self.assertEqual([s["kind"] for s in record["segments"]],
                         ["cylinder", "taper", "taper", "cylinder", "cylinder"])


if __name__ == "__main__":
    unittest.main()
