import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from maido.cli.main import main


class CliBundleCommandTests(unittest.TestCase):
    def test_bundle_init_writes_manifest_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")

            output_path = os.path.join(temp_dir, "custom-maido.json")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "bundle",
                        "init",
                        video_path,
                        "--sync-point",
                        "4.5",
                        "--center-x",
                        "100",
                        "--center-y",
                        "200",
                        "--max-width",
                        "500",
                        "--output",
                        output_path,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.isfile(output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)

            self.assertEqual(manifest["video_file"], "source.mp4")
            self.assertEqual(manifest["center"], {"x": 100.0, "y": 200.0})
            self.assertEqual(
                manifest["max_dimensions"], {"width": 500.0, "height": None}
            )
            self.assertIn("Wrote manifest:", stdout.getvalue())

    def test_bundle_init_rejects_partial_center(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "bundle",
                        "init",
                        video_path,
                        "--sync-point",
                        "4.5",
                        "--center-x",
                        "100",
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn(
                "center requires both --center-x and --center-y", stdout.getvalue()
            )

    def test_bundle_init_rejects_min_width_greater_than_max_width(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "bundle",
                        "init",
                        video_path,
                        "--sync-point",
                        "4.5",
                        "--min-width",
                        "600",
                        "--max-width",
                        "500",
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn(
                "min_dimensions.width cannot exceed max_dimensions.width",
                stdout.getvalue(),
            )

    def test_bundle_pack_creates_bundle_when_probe_succeeds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            manifest_path = os.path.join(temp_dir, "maido.json")
            output_path = os.path.join(temp_dir, "packed.maido.zip")

            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "version": "1",
                        "video_file": "source.mp4",
                        "sync_point_seconds": 4.5,
                        "max_dimensions": {"width": 500, "height": None},
                    },
                    handle,
                )

            stdout = io.StringIO()
            with mock.patch(
                "maido.bundle.packing.probe_video_file",
                return_value={
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 10.0,
                    "fps": 30.0,
                },
            ):
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "bundle",
                            "pack",
                            video_path,
                            manifest_path,
                            "--output",
                            output_path,
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.isfile(output_path))
            self.assertIn("Created bundle:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
