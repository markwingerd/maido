import unittest

from maido.security.errors import SyncConflictError
from maido.sync import plan_sync


class SyncPlannerTests(unittest.TestCase):
    def test_plan_sync_delays_supporting_clip_when_core_sync_is_later(self):
        result = plan_sync(
            [
                {
                    "bundle_id": "core",
                    "manifest": {"sync_point_seconds": 5.0},
                    "probe": {"duration_seconds": 10.0},
                },
                {
                    "bundle_id": "support",
                    "manifest": {"sync_point_seconds": 2.0},
                    "probe": {"duration_seconds": 7.0},
                },
            ],
            core_input=0,
            entry_fade_seconds=0.2,
        )

        self.assertEqual(result["output_duration_seconds"], 10.0)
        support = result["clips"][1]
        self.assertEqual(support["output_start_seconds"], 3.0)
        self.assertEqual(support["trim_start_seconds"], 0.0)
        self.assertEqual(support["output_end_seconds"], 10.0)
        self.assertEqual(support["leading_black_seconds"], 3.0)
        self.assertEqual(support["applied_entry_fade_seconds"], 0.2)

    def test_plan_sync_trims_supporting_clip_when_core_sync_is_earlier(self):
        result = plan_sync(
            [
                {
                    "bundle_id": "core",
                    "manifest": {"sync_point_seconds": 2.0},
                    "probe": {"duration_seconds": 10.0},
                },
                {
                    "bundle_id": "support",
                    "manifest": {"sync_point_seconds": 5.0},
                    "probe": {"duration_seconds": 8.0},
                },
            ],
            core_input=0,
            entry_fade_seconds=0.2,
        )

        support = result["clips"][1]
        self.assertEqual(support["output_start_seconds"], 0.0)
        self.assertEqual(support["trim_start_seconds"], 3.0)
        self.assertEqual(support["trim_end_seconds"], 8.0)
        self.assertEqual(support["output_end_seconds"], 5.0)
        self.assertEqual(support["trailing_black_seconds"], 5.0)
        self.assertEqual(support["applied_entry_fade_seconds"], 0.0)

    def test_plan_sync_uses_core_duration_as_output_duration(self):
        result = plan_sync(
            [
                {
                    "bundle_id": "support",
                    "manifest": {"sync_point_seconds": 1.0},
                    "probe": {"duration_seconds": 20.0},
                },
                {
                    "bundle_id": "core",
                    "manifest": {"sync_point_seconds": 4.0},
                    "probe": {"duration_seconds": 12.0},
                },
            ],
            core_input=1,
        )

        self.assertEqual(result["output_duration_seconds"], 12.0)
        self.assertEqual(result["output_sync_point_seconds"], 4.0)
        core = result["clips"][1]
        self.assertEqual(core["output_end_seconds"], 12.0)

    def test_plan_sync_rejects_missing_sync_point(self):
        with self.assertRaises(SyncConflictError):
            plan_sync(
                [
                    {
                        "bundle_id": "core",
                        "manifest": {},
                        "probe": {"duration_seconds": 12.0},
                    },
                ],
                core_input=0,
            )


if __name__ == "__main__":
    unittest.main()
