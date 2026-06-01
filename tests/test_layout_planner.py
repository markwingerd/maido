import unittest

from maido.layout import plan_layout
from maido.security.errors import LayoutConflictError


class LayoutPlannerTests(unittest.TestCase):
    def test_horizontal_layout_places_core_left_of_center_for_even_count(self):
        result = plan_layout(
            [
                {"bundle_id": "a", "preferred_direction": "left"},
                {"bundle_id": "core"},
                {"bundle_id": "c", "preferred_direction": "right"},
                {"bundle_id": "d"},
            ],
            core_input=1,
            layout_mode="horizontal",
        )

        self.assertEqual([entry["bundle_id"] for entry in result], ["a", "core", "c", "d"])
        self.assertEqual(result[1]["cell_index"], 1)
        self.assertEqual(result[1]["placement_direction"], "center")

    def test_horizontal_layout_overflows_same_side_preference_in_cli_order(self):
        result = plan_layout(
            [
                {"bundle_id": "left_a", "preferred_direction": "left"},
                {"bundle_id": "core"},
                {"bundle_id": "left_b", "preferred_direction": "left"},
            ],
            core_input=1,
            layout_mode="horizontal",
        )

        self.assertEqual(
            [entry["bundle_id"] for entry in result],
            ["left_a", "core", "left_b"],
        )
        self.assertTrue(result[0]["preference_satisfied"])
        self.assertFalse(result[2]["preference_satisfied"])

    def test_vertical_layout_places_core_above_center_for_even_count(self):
        result = plan_layout(
            [
                {"bundle_id": "top", "preferred_direction": "up"},
                {"bundle_id": "core"},
                {"bundle_id": "bottom", "preferred_direction": "down"},
                {"bundle_id": "extra"},
            ],
            core_input=1,
            layout_mode="vertical",
        )

        self.assertEqual([entry["bundle_id"] for entry in result], ["top", "core", "bottom", "extra"])
        self.assertEqual(result[1]["cell_index"], 1)
        self.assertEqual(result[2]["placement_direction"], "down")

    def test_horizontal_layout_rejects_vertical_preference(self):
        with self.assertRaises(LayoutConflictError):
            plan_layout(
                [
                    {"bundle_id": "core"},
                    {"bundle_id": "bad", "preferred_direction": "up"},
                ],
                core_input=0,
                layout_mode="horizontal",
            )

    def test_vertical_layout_rejects_horizontal_preference(self):
        with self.assertRaises(LayoutConflictError):
            plan_layout(
                [
                    {"bundle_id": "core"},
                    {"bundle_id": "bad", "preferred_direction": "left"},
                ],
                core_input=0,
                layout_mode="vertical",
            )

    def test_layout_allocates_variable_horizontal_widths(self):
        result = plan_layout(
            [
                {
                    "bundle_id": "left",
                    "min_dimensions": {"width": 240.0, "height": None},
                    "max_dimensions": {"width": 288.0, "height": None},
                },
                {
                    "bundle_id": "core",
                    "min_dimensions": {"width": 640.0, "height": None},
                },
                {
                    "bundle_id": "right",
                    "min_dimensions": {"width": 240.0, "height": None},
                    "max_dimensions": {"width": 288.0, "height": None},
                },
            ],
            core_input=1,
            layout_mode="horizontal",
            canvas_width=1280,
            canvas_height=720,
        )

        self.assertEqual(result[0]["cell_width"], 288.0)
        self.assertEqual(result[1]["cell_width"], 704.0)
        self.assertEqual(result[2]["cell_width"], 288.0)
        self.assertEqual(result[1]["cell_x"], 288.0)

    def test_layout_centers_unused_space_when_maximums_cannot_fill_canvas(self):
        result = plan_layout(
            [
                {
                    "bundle_id": "core",
                    "max_dimensions": {"width": 300.0, "height": None},
                },
                {
                    "bundle_id": "other",
                    "max_dimensions": {"width": 200.0, "height": None},
                },
            ],
            core_input=0,
            layout_mode="horizontal",
            canvas_width=600,
            canvas_height=300,
        )

        self.assertEqual(result[0]["cell_width"], 300.0)
        self.assertEqual(result[1]["cell_width"], 200.0)
        self.assertEqual(result[0]["cell_x"], 50.0)
        self.assertEqual(result[1]["cell_x"], 350.0)

    def test_layout_rejects_combined_minimums_without_override(self):
        with self.assertRaises(LayoutConflictError):
            plan_layout(
                [
                    {"bundle_id": "core", "min_dimensions": {"width": 640.0, "height": None}},
                    {"bundle_id": "other", "min_dimensions": {"width": 240.0, "height": None}},
                    {"bundle_id": "other2", "min_dimensions": {"width": 240.0, "height": None}},
                ],
                core_input=0,
                layout_mode="horizontal",
                canvas_width=1000,
                canvas_height=300,
            )

    def test_layout_override_keeps_core_minimum_and_shares_remaining_space(self):
        result = plan_layout(
            [
                {"bundle_id": "core", "min_dimensions": {"width": 640.0, "height": None}},
                {"bundle_id": "other", "min_dimensions": {"width": 240.0, "height": None}},
                {"bundle_id": "other2", "min_dimensions": {"width": 240.0, "height": None}},
            ],
            core_input=0,
            layout_mode="horizontal",
            canvas_width=1000,
            canvas_height=300,
            allow_size_override=True,
        )

        self.assertEqual([entry["bundle_id"] for entry in result], ["other", "core", "other2"])
        self.assertEqual(result[0]["cell_width"], 180.0)
        self.assertEqual(result[1]["cell_width"], 640.0)
        self.assertEqual(result[2]["cell_width"], 180.0)

    def test_layout_preserves_remaining_cli_order_after_preferred_assignment(self):
        result = plan_layout(
            [
                {"bundle_id": "left_a", "preferred_direction": "left"},
                {"bundle_id": "core"},
                {"bundle_id": "right_a", "preferred_direction": "right"},
                {"bundle_id": "left_b", "preferred_direction": "left"},
                {"bundle_id": "free"},
            ],
            core_input=1,
            layout_mode="horizontal",
        )

        self.assertEqual(
            [entry["bundle_id"] for entry in result],
            ["left_a", "left_b", "core", "right_a", "free"],
        )
        self.assertTrue(result[1]["preference_satisfied"])
        self.assertIsNone(result[4]["preference_satisfied"])


if __name__ == "__main__":
    unittest.main()
