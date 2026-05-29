import unittest

from maido.crop import plan_crop, plan_crop_for_manifest
from maido.security.errors import CropConflictError


class CropPlannerTests(unittest.TestCase):
    def test_plan_crop_uses_largest_available_crop_for_target_aspect(self):
        result = plan_crop(
            source_width=1920,
            source_height=1080,
            cell_width=640,
            cell_height=640,
        )

        self.assertEqual(result["crop_width"], 1080.0)
        self.assertEqual(result["crop_height"], 1080.0)
        self.assertEqual(result["crop_x"], 420.0)
        self.assertEqual(result["crop_y"], 0.0)

    def test_plan_crop_respects_max_dimensions(self):
        result = plan_crop(
            source_width=1920,
            source_height=1080,
            cell_width=640,
            cell_height=640,
            max_dimensions={"width": 800, "height": None},
        )

        self.assertEqual(result["crop_width"], 800.0)
        self.assertEqual(result["crop_height"], 800.0)
        self.assertEqual(result["crop_x"], 560.0)
        self.assertEqual(result["crop_y"], 140.0)

    def test_plan_crop_clamps_requested_center_to_source_bounds(self):
        result = plan_crop(
            source_width=1920,
            source_height=1080,
            cell_width=1000,
            cell_height=500,
            center={"x": 1900, "y": 50},
            max_dimensions={"width": 1000, "height": None},
        )

        self.assertEqual(result["crop_width"], 1000.0)
        self.assertEqual(result["crop_height"], 500.0)
        self.assertEqual(result["crop_x"], 920.0)
        self.assertEqual(result["crop_y"], 0.0)

    def test_plan_crop_rejects_impossible_constraints(self):
        with self.assertRaises(CropConflictError):
            plan_crop(
                source_width=1920,
                source_height=1080,
                cell_width=640,
                cell_height=640,
                min_dimensions={"width": 1200, "height": None},
            )

    def test_plan_crop_rejects_min_width_greater_than_max_width(self):
        with self.assertRaises(CropConflictError):
            plan_crop(
                source_width=1920,
                source_height=1080,
                cell_width=640,
                cell_height=640,
                min_dimensions={"width": 700, "height": None},
                max_dimensions={"width": 500, "height": None},
            )

    def test_plan_crop_for_manifest_uses_manifest_constraints(self):
        manifest = {
            "center": {"x": 1200, "y": 540},
            "min_dimensions": {"width": None, "height": 400},
            "max_dimensions": {"width": 900, "height": None},
        }
        probe_info = {
            "width": 1920,
            "height": 1080,
        }

        result = plan_crop_for_manifest(manifest, probe_info, 640, 640)

        self.assertEqual(result["crop_width"], 900.0)
        self.assertEqual(result["crop_height"], 900.0)
        self.assertEqual(result["crop_x"], 750.0)
        self.assertEqual(result["crop_y"], 90.0)


if __name__ == "__main__":
    unittest.main()
