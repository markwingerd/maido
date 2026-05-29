import os
import tempfile
import unittest
import zipfile

from maido.security.archive import inspect_zip_file
from maido.security.errors import ArchiveError


class ArchiveValidationTests(unittest.TestCase):
    def test_valid_bundle_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "valid.maido.zip")
            with zipfile.ZipFile(bundle_path, "w") as archive:
                archive.writestr("maido.json", "{}")
                archive.writestr("source.mp4", b"video-bytes")

            inspection = inspect_zip_file(bundle_path)
            self.assertEqual(inspection["manifest_name"], "maido.json")
            self.assertEqual(inspection["video_name"], "source.mp4")

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "bad.maido.zip")
            with zipfile.ZipFile(bundle_path, "w") as archive:
                archive.writestr("../maido.json", "{}")
                archive.writestr("source.mp4", b"video-bytes")

            with self.assertRaises(ArchiveError):
                inspect_zip_file(bundle_path)

    def test_extra_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = os.path.join(temp_dir, "extra.maido.zip")
            with zipfile.ZipFile(bundle_path, "w") as archive:
                archive.writestr("maido.json", "{}")
                archive.writestr("source.mp4", b"video-bytes")
                archive.writestr("notes.txt", "hello")

            with self.assertRaises(ArchiveError):
                inspect_zip_file(bundle_path)


if __name__ == "__main__":
    unittest.main()
