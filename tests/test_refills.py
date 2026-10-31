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
            "format": "unknown", "measurement_status": "measured",
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

    def test_empty_profile_is_allowed_only_for_incomplete_placeholder(self):
        record = self.record()
        record["segments"] = []
        with self.assertRaisesRegex(ValueError, "nonempty"):
            validate_refill(record)
        record["measurement_status"] = "incomplete"
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

    def test_catalog_choices_reject_unlisted_values(self):
        for field, invalid in (("format", "misc"), ("ink_type", "magic"),
                               ("tip_shape", "sharp")):
            with self.subTest(field=field):
                record = self.record()
                record[field] = invalid
                with self.assertRaisesRegex(ValueError, field):
                    validate_refill(record)

    def test_photo_groups_accept_paths_and_reject_malformed_values(self):
        record = self.record()
        record["pen_photos"] = ["/assets/source-pen.jpg"]
        record["ink_photos"] = ["/assets/writing-sample.jpg"]
        record["ink_notes"] = "Smooth, dark blue line."
        result = validate_refill(record)
        self.assertEqual(result["pen_photos"], record["pen_photos"])
        self.assertEqual(result["ink_photos"], record["ink_photos"])
        record["ink_photos"] = [""]
        with self.assertRaisesRegex(ValueError, "ink_photos"):
            validate_refill(record)

    def test_source_pens_are_optional_names(self):
        record = self.record()
        record["source_pens"] = ["Pilot Precise V5 RT", "Pilot Hi-Techpoint V5 RT"]
        self.assertEqual(validate_refill(record)["source_pens"], record["source_pens"])
        record["source_pens"] = [""]
        with self.assertRaisesRegex(ValueError, "source_pens"):
            validate_refill(record)

    def test_pilot_shared_inks_and_g_tec_measurements(self):
        records = {record["id"]: record for record in load_refills()}
        self.assertNotIn("pilot-hi-techpoint-v5-rt", records)
        self.assertNotIn("pilot-precise-v5-rt", records)
        self.assertNotIn("pilot-g-2-07", records)
        self.assertNotIn("pilot-g-2-penstylus", records)
        expected = {
            "pilot-bxs-v5rt": ([2.9, 8.9, 11.9, 15.6, 20.5, 21.5, 110],
                                 ["Pilot Hi Techpoint V5 RT", "Pilot Precise V5 RT"]),
            "pilot-lg-2rf": ([3.5, 9, 15, 19.5, 110.5],
                              ["Pilot G-2 07", "Pilot G-2 Stylus"]),
            "pilot-g-tec-c4": ([1.9, 3.4, 5, 6.3, 9, 10.5, 13.8, 15.5, 115.7], None),
        }
        for refill_id, (ends, source_pens) in expected.items():
            with self.subTest(refill_id=refill_id):
                record = records[refill_id]
                self.assertTrue(record["geometry_ready"])
                self.assertEqual([segment["end_distance_mm"] for segment in record["segments"]], ends)
                self.assertEqual(record.get("source_pens"), source_pens)
        self.assertEqual(
            [(segment["diameter_start_mm"], segment["diameter_end_mm"])
             for segment in records["pilot-g-tec-c4"]["segments"] if segment["kind"] == "taper"],
            [(1.5, 2.6), (2.5, 3.5)],
        )
        self.assertEqual(records["pilot-lg-2rf"]["segments"][0]["kind"], "taper")

    def test_zebra_jf_sizes_share_measured_geometry(self):
        records = {record["id"]: record for record in load_refills()}
        small = records["zebra-jf-03"]
        medium = records["zebra-jf-05"]
        large = records["zebra-jf-07"]
        self.assertTrue(small["geometry_ready"])
        self.assertTrue(medium["geometry_ready"])
        self.assertTrue(large["geometry_ready"])
        self.assertEqual(small["tip_size_mm"], 0.3)
        self.assertEqual(medium["tip_size_mm"], 0.5)
        self.assertEqual(large["tip_size_mm"], 0.7)
        self.assertEqual(small["segments"], medium["segments"])
        self.assertEqual(small["segments"], large["segments"])
        self.assertEqual(small["overall_length_mm"], 111.1)
        self.assertEqual(small["segments"][-1]["diameter_mm"], 6.1)
        self.assertEqual(small["segments"][0]["kind"], "taper")

    def test_tg31880_uses_tip_referenced_measurements(self):
        record = next(r for r in load_refills() if r["id"] == "tian-zhuo-hoshi-tg31880")
        self.assertEqual(record["overall_length_mm"], 130)
        self.assertEqual([s["end_distance_mm"] for s in record["segments"]],
                         [3, 7.5, 14.2, 15.5, 130])
        self.assertEqual([s["kind"] for s in record["segments"]],
                         ["cylinder", "taper", "taper", "cylinder", "cylinder"])

    def test_jihekj_corrected_end_distances(self):
        record = next(r for r in load_refills() if r["id"] == "jihekj-unspecified-05")
        self.assertEqual(record["overall_length_mm"], 130.7)
        self.assertEqual([s["end_distance_mm"] for s in record["segments"]],
                         [1.4, 3.5, 8.0, 14.5, 16.0, 130.7])


if __name__ == "__main__":
    unittest.main()
