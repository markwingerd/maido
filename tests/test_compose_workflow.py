import json
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from maido.composition.workflow import compose_bundles_to_file
from maido.security.errors import CompositionPlanError


class ComposeWorkflowTests(unittest.TestCase):
    def test_compose_bundles_to_file_orchestrates_planning_and_render(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            left_bundle = self._write_bundle(temp_dir, "left.maido.zip", 2.0, "left")
            core_bundle = self._write_bundle(temp_dir, "core.maido.zip", 5.0, None)
            output_path = os.path.join(temp_dir, "output.mp4")

            with mock.patch(
                "maido.composition.workflow.probe_video_file",
                return_value={
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 10.0,
                    "fps": 30.0,
                },
            ):
                with mock.patch(
                    "maido.composition.workflow.render_plan_to_file",
                    side_effect=self._fake_render_result,
                ) as render_mock:
                    result = compose_bundles_to_file(
                        [left_bundle, core_bundle],
                        core_input=1,
                        output_path=output_path,
                        canvas_width=1920,
                        canvas_height=1080,
                        layout_mode="horizontal",
                        audio_mode="mute",
                        entry_fade_seconds=0.2,
                    )

            self.assertEqual(result["render_result"]["output_path"], output_path)
            self.assertEqual(result["composition_plan"]["clip_count"], 2)
            self.assertEqual(result["render_plan"]["audio"]["mode"], "mute")
            self.assertEqual(render_mock.call_count, 1)

    def test_compose_bundles_to_file_requires_two_bundles(self):
        with self.assertRaises(CompositionPlanError):
            compose_bundles_to_file(
                ["one.maido.zip"],
                core_input=0,
                output_path="output.mp4",
                canvas_width=1920,
                canvas_height=1080,
            )

    def _write_bundle(self, temp_dir, filename, sync_point_seconds, preferred_direction):
        bundle_path = os.path.join(temp_dir, filename)
        manifest = {
            "version": "1",
            "video_file": "source.mp4",
            "sync_point_seconds": sync_point_seconds,
        }
        if preferred_direction is not None:
            manifest["preferred_direction"] = preferred_direction

        with zipfile.ZipFile(bundle_path, "w") as archive:
            archive.writestr("maido.json", json.dumps(manifest))
            archive.writestr("source.mp4", b"video-bytes")

        return bundle_path

    def _fake_render_result(self, render_plan, output_path, fps=None, codec=None, audio_codec=None):
        return {
            "output_path": output_path,
            "fps": fps or 30.0,
            "codec": codec,
            "audio_codec": audio_codec,
            "audio_mode": render_plan["audio"]["mode"],
            "clip_count": len(render_plan["clips"]),
        }


if __name__ == "__main__":
    unittest.main()
