import unittest

from maido.composition import plan_composition
from maido.security.errors import CompositionPlanError, CropConflictError


class CompositionPlannerTests(unittest.TestCase):
    def test_plan_composition_merges_layout_and_crop(self):
        result = plan_composition(
            [
                {
                    "bundle_id": "left",
                    "manifest": {
                        "preferred_direction": "left",
                        "center": {"x": 400, "y": 300},
                    },
                    "probe": {"width": 800, "height": 600},
                },
                {
                    "bundle_id": "core",
                    "manifest": {
                        "center": {"x": 960, "y": 540},
                        "min_dimensions": {"width": None, "height": 500},
                    },
                    "probe": {"width": 1920, "height": 1080},
                },
                {
                    "bundle_id": "right",
                    "manifest": {
                        "preferred_direction": "right",
                        "max_dimensions": {"width": 400, "height": None},
                    },
                    "probe": {"width": 1280, "height": 720},
                },
            ],
            core_input=1,
            canvas_width=1920,
            canvas_height=1080,
            layout_mode="horizontal",
        )

        self.assertEqual(result["clip_count"], 3)
        self.assertEqual([clip["bundle_id"] for clip in result["clips"]], ["left", "core", "right"])
        self.assertEqual(result["clips"][1]["role"], "core")
        self.assertEqual(result["clips"][1]["layout"]["cell_width"], 640.0)
        self.assertEqual(result["clips"][0]["crop"]["crop_width"], 355.55555555555554)
        self.assertEqual(result["clips"][2]["crop"]["crop_width"], 400.0)

    def test_plan_composition_rejects_missing_probe_dimensions(self):
        with self.assertRaises(CompositionPlanError):
            plan_composition(
                [
                    {
                        "bundle_id": "core",
                        "manifest": {},
                        "probe": {"width": 1920},
                    },
                ],
                core_input=0,
                canvas_width=1920,
                canvas_height=1080,
            )

    def test_plan_composition_propagates_crop_conflicts(self):
        with self.assertRaises(CropConflictError):
            plan_composition(
                [
                    {
                        "bundle_id": "core",
                        "manifest": {
                            "min_dimensions": {"width": 1000, "height": None},
                        },
                        "probe": {"width": 1000, "height": 500},
                    },
                    {
                        "bundle_id": "other",
                        "manifest": {},
                        "probe": {"width": 1000, "height": 500},
                    },
                ],
                core_input=0,
                canvas_width=1000,
                canvas_height=1000,
                layout_mode="horizontal",
            )


if __name__ == "__main__":
    unittest.main()
