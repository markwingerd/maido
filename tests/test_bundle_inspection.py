import json
import os
import tempfile
import unittest
import zipfile

from maido.bundle.inspection import inspect_bundle_path
from maido.security.errors import ManifestValidationError


class BundleInspectionTests(unittest.TestCase):
    def test_inspect_bundle_returns_manifest_and_probe_info(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "sample.maido.zip")
            manifest = {
                "version": "1",
                "video_file": "source.mp4",
                "sync_point_seconds": 4.5,
                "center": {"x": 200, "y": 300},
                "min_dimensions": {"width": None, "height": 200},
            }

            with zipfile.ZipFile(bundle_path, "w") as archive:
                archive.writestr("maido.json", json.dumps(manifest))
                archive.writestr("source.mp4", b"video-bytes")

            report = inspect_bundle_path(bundle_path, probe_file=self._fake_probe)

            self.assertEqual(report["manifest"]["video_file"], "source.mp4")
            self.assertEqual(report["probe"]["width"], 1920)
            self.assertEqual(report["probe"]["height"], 1080)

    def test_inspect_bundle_rejects_manifest_video_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "sample.maido.zip")
            manifest = {
                "version": "1",
                "video_file": "different.mp4",
                "sync_point_seconds": 4.5,
            }

            with zipfile.ZipFile(bundle_path, "w") as archive:
                archive.writestr("maido.json", json.dumps(manifest))
                archive.writestr("source.mp4", b"video-bytes")

            with self.assertRaises(ManifestValidationError):
                inspect_bundle_path(bundle_path, probe_file=self._fake_probe)

    def _fake_probe(self, _path):
        return {
            "width": 1920,
            "height": 1080,
            "duration_seconds": 10.0,
            "fps": 30.0,
        }


if __name__ == "__main__":
    unittest.main()
