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

    def test_layout_includes_horizontal_cell_geometry(self):
        result = plan_layout(
            [
                {"bundle_id": "core"},
                {"bundle_id": "other"},
            ],
            core_input=0,
            layout_mode="horizontal",
            canvas_width=1920,
            canvas_height=1080,
        )

        self.assertEqual(result[0]["cell_width"], 960.0)
        self.assertEqual(result[1]["cell_x"], 960.0)
        self.assertEqual(result[1]["cell_height"], 1080.0)

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
