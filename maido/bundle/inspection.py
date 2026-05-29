from maido.bundle.reader import open_bundle
from maido.manifest.schema import (
    load_manifest_file,
    validate_manifest,
    validate_manifest_against_probe,
)
from maido.probe.video import probe_video_file
from maido.security.errors import ManifestValidationError


def inspect_bundle_path(bundle_path, probe_file=None):
    probe_file = probe_file or probe_video_file

    with open_bundle(bundle_path) as opened_bundle:
        manifest_raw = load_manifest_file(opened_bundle["manifest_path"])
        manifest = validate_manifest(manifest_raw)

        if manifest["video_file"] != opened_bundle["video_name"]:
            raise ManifestValidationError(
                "video_file does not match the video file in the bundle",
                field="video_file",
                declared_video_file=manifest["video_file"],
                actual_video_file=opened_bundle["video_name"],
            )

        probe_info = probe_file(opened_bundle["video_path"])
        validate_manifest_against_probe(manifest, probe_info)

        return {
            "bundle_path": str(bundle_path),
            "archive": opened_bundle["inspection"],
            "manifest": manifest,
            "probe": probe_info,
        }
