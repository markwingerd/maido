import os
import zipfile

from ..manifest.schema import (
    load_manifest_file,
    validate_manifest,
    validate_manifest_against_probe,
)
from ..probe.video import probe_video_file
from ..security.archive import ALLOWED_VIDEO_EXTENSIONS, MANIFEST_FILENAME
from ..security.errors import MaidoError, ManifestValidationError


def pack_bundle(
    video_path, manifest_path, output_path=None, probe_file=None, overwrite=False
):
    video_path = os.path.abspath(video_path)
    manifest_path = os.path.abspath(manifest_path)
    probe_file = probe_file or probe_video_file

    if not os.path.isfile(video_path):
        raise MaidoError("video file does not exist", path=video_path)

    if not os.path.isfile(manifest_path):
        raise MaidoError("manifest file does not exist", path=manifest_path)

    extension = os.path.splitext(video_path)[1].lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise MaidoError(
            "video file extension is not supported",
            path=video_path,
            allowed_extensions=sorted(ALLOWED_VIDEO_EXTENSIONS),
        )

    manifest_raw = load_manifest_file(manifest_path)
    manifest = validate_manifest(manifest_raw)

    video_name = os.path.basename(video_path)
    if manifest["video_file"] != video_name:
        raise ManifestValidationError(
            "video_file does not match the selected video file",
            field="video_file",
            declared_video_file=manifest["video_file"],
            actual_video_file=video_name,
        )

    probe_info = probe_file(video_path)
    validate_manifest_against_probe(manifest, probe_info)

    final_output_path = output_path or _default_output_path(video_path)
    final_output_path = os.path.abspath(final_output_path)

    if os.path.exists(final_output_path) and not overwrite:
        raise MaidoError(
            "output bundle already exists; pass overwrite to replace it",
            path=final_output_path,
        )

    os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

    with zipfile.ZipFile(
        final_output_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.write(manifest_path, arcname=MANIFEST_FILENAME)
        archive.write(video_path, arcname=video_name)

    return {
        "bundle_path": final_output_path,
        "manifest_path": manifest_path,
        "video_path": video_path,
    }


def _default_output_path(video_path):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    parent_dir = os.path.dirname(video_path) or "."
    return os.path.join(parent_dir, f"{base_name}.maido.zip")
