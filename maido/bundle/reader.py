import tempfile
from contextlib import contextmanager

from ..security.archive import extract_validated_zip, inspect_zip_file


@contextmanager
def open_bundle(bundle_path, limits=None):
    inspection = inspect_zip_file(bundle_path, limits=limits)

    with tempfile.TemporaryDirectory(prefix="maido_bundle_") as temp_dir:
        extracted = extract_validated_zip(bundle_path, temp_dir, inspection=inspection)
        yield {
            "bundle_path": str(bundle_path),
            "temp_dir": temp_dir,
            "inspection": inspection,
            "manifest_path": extracted["manifest_path"],
            "video_path": extracted["video_path"],
            "manifest_name": extracted["manifest_name"],
            "video_name": extracted["video_name"],
        }
