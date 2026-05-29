import unittest

from maido.manifest.schema import validate_manifest, validate_manifest_against_probe
from maido.security.errors import ManifestValidationError


class ManifestSchemaTests(unittest.TestCase):
    def test_validate_manifest_accepts_valid_data(self):
        manifest = validate_manifest(
            {
                "version": "1",
                "video_file": "source.mp4",
                "sync_point_seconds": 4.5,
                "label": "Camera A",
                "center": {"x": 200, "y": 300},
                "min_dimensions": {"width": None, "height": 200},
                "preferred_direction": "left",
            }
        )

        self.assertEqual(manifest["video_file"], "source.mp4")
        self.assertEqual(manifest["preferred_direction"], "left")
        self.assertEqual(manifest["center"], {"x": 200.0, "y": 300.0})
        self.assertEqual(manifest["min_dimensions"], {"width": None, "height": 200.0})

    def test_validate_manifest_rejects_partial_center(self):
        with self.assertRaises(ManifestValidationError):
            validate_manifest(
                {
                    "version": "1",
                    "video_file": "source.mp4",
                    "sync_point_seconds": 4.5,
                    "center": {"x": 100},
                }
            )

    def test_validate_manifest_rejects_empty_min_dimensions(self):
        with self.assertRaises(ManifestValidationError):
            validate_manifest(
                {
                    "version": "1",
                    "video_file": "source.mp4",
                    "sync_point_seconds": 4.5,
                    "min_dimensions": {},
                }
            )

    def test_validate_manifest_rejects_invalid_direction(self):
        with self.assertRaises(ManifestValidationError):
            validate_manifest(
                {
                    "version": "1",
                    "video_file": "source.mp4",
                    "sync_point_seconds": 4.5,
                    "preferred_direction": "north",
                }
            )

    def test_probe_validation_rejects_sync_past_duration(self):
        manifest = validate_manifest(
            {
                "version": "1",
                "video_file": "source.mp4",
                "sync_point_seconds": 12.0,
            }
        )

        with self.assertRaises(ManifestValidationError):
            validate_manifest_against_probe(
                manifest,
                {
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 10.0,
                    "fps": 30.0,
                },
            )


if __name__ == "__main__":
    unittest.main()
