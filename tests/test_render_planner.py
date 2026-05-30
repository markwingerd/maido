import unittest

from maido.composition import plan_composition
from maido.render import plan_render
from maido.security.errors import RenderPlanError


class RenderPlannerTests(unittest.TestCase):
    def test_plan_render_builds_core_audio_plan(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "source_path": "core.mp4",
                    "manifest": {
                        "sync_point_seconds": 4.0,
                    },
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
                {
                    "bundle_id": "support",
                    "source_path": "support.mp4",
                    "manifest": {
                        "sync_point_seconds": 2.0,
                        "preferred_direction": "right",
                    },
                    "probe": {
                        "width": 1280,
                        "height": 720,
                        "duration_seconds": 8.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
            layout_mode="horizontal",
            entry_fade_seconds=0.2,
        )

        render_plan = plan_render(composition_plan)

        self.assertEqual(render_plan["audio"]["mode"], "core")
        self.assertEqual(render_plan["audio"]["core_bundle_id"], "core")
        self.assertIsNone(render_plan["audio"]["audio_file"])
        self.assertTrue(render_plan["clips"][0]["render_audio"])
        self.assertFalse(render_plan["clips"][1]["render_audio"])
        self.assertEqual(render_plan["clips"][1]["output_start_seconds"], 2.0)

    def test_plan_render_supports_external_audio(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "source_path": "core.mp4",
                    "manifest": {
                        "sync_point_seconds": 4.0,
                    },
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
        )

        render_plan = plan_render(
            composition_plan,
            audio_mode="file",
            audio_file="music.mp3",
            background_color=(0, 0, 0),
        )

        self.assertEqual(render_plan["audio"]["mode"], "file")
        self.assertEqual(render_plan["audio"]["audio_file"], "music.mp3")
        self.assertEqual(render_plan["background_color"], (0.0, 0.0, 0.0))
        self.assertFalse(render_plan["clips"][0]["render_audio"])

    def test_plan_render_requires_source_paths(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "manifest": {
                        "sync_point_seconds": 4.0,
                    },
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
        )

        with self.assertRaises(RenderPlanError):
            plan_render(composition_plan)

    def test_plan_render_rejects_audio_file_for_non_file_mode(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "source_path": "core.mp4",
                    "manifest": {
                        "sync_point_seconds": 4.0,
                    },
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
        )

        with self.assertRaises(RenderPlanError):
            plan_render(composition_plan, audio_mode="core", audio_file="music.mp3")


if __name__ == "__main__":
    unittest.main()
