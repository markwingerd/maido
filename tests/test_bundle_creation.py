import os
import tempfile
import unittest
import zipfile

from maido.bundle.inspection import inspect_bundle_path
from maido.bundle.packing import pack_bundle
from maido.manifest.template import build_manifest_data, write_manifest_file
from maido.security.errors import ManifestValidationError


class BundleCreationTests(unittest.TestCase):
    def test_build_manifest_data_creates_valid_manifest(self):
        manifest = build_manifest_data(
            video_file="source.mp4",
            sync_point_seconds=4.5,
            center={"x": 100, "y": 200},
            min_dimensions={"width": None, "height": 150},
            preferred_direction="right",
        )

        self.assertEqual(manifest["version"], "1")
        self.assertEqual(manifest["video_file"], "source.mp4")
        self.assertEqual(manifest["preferred_direction"], "right")

    def test_pack_bundle_creates_inspectable_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            manifest_path = os.path.join(temp_dir, "maido.json")
            output_path = os.path.join(temp_dir, "output.maido.zip")

            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")

            manifest = build_manifest_data(
                video_file=video_path,
                sync_point_seconds=4.5,
                center={"x": 200, "y": 300},
            )
            write_manifest_file(manifest_path, manifest)

            result = pack_bundle(
                video_path,
                manifest_path,
                output_path=output_path,
                probe_file=self._fake_probe,
            )

            self.assertEqual(result["bundle_path"], os.path.abspath(output_path))
            self.assertTrue(os.path.isfile(output_path))

            with zipfile.ZipFile(output_path, "r") as archive:
                self.assertEqual(
                    sorted(archive.namelist()), ["maido.json", "source.mp4"]
                )

            report = inspect_bundle_path(output_path, probe_file=self._fake_probe)
            self.assertEqual(report["manifest"]["video_file"], "source.mp4")
            self.assertEqual(report["probe"]["duration_seconds"], 10.0)

    def test_pack_bundle_rejects_manifest_video_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            manifest_path = os.path.join(temp_dir, "maido.json")

            with open(video_path, "wb") as handle:
                handle.write(b"video-bytes")

            write_manifest_file(
                manifest_path,
                {
                    "version": "1",
                    "video_file": "other.mp4",
                    "sync_point_seconds": 4.5,
                },
            )

            with self.assertRaises(ManifestValidationError):
                pack_bundle(video_path, manifest_path, probe_file=self._fake_probe)

    def _fake_probe(self, _path):
        return {
            "width": 1920,
            "height": 1080,
            "duration_seconds": 10.0,
            "fps": 30.0,
        }


if __name__ == "__main__":
    unittest.main()
