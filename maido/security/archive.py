import os
import re
import shutil
import stat
import zipfile
from pathlib import PurePosixPath

from .errors import ArchiveError

MANIFEST_FILENAME = "maido.json"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
DEFAULT_LIMITS = {
    "max_files": 2,  # Only video file and manifest for now. Audio might be added later
    "max_total_uncompressed_bytes": 64 * 1024 * 1024,  # 64 MiB
    "max_single_file_uncompressed_bytes": 16 * 1024 * 1024,  # 16 MiB
}


def inspect_zip_file(zip_path, limits=None):
    applied_limits = dict(DEFAULT_LIMITS)
    if limits:
        applied_limits.update(limits)

    if not zipfile.is_zipfile(zip_path):
        raise ArchiveError(
            "input is not a valid zip archive", bundle_path=str(zip_path)
        )

    with zipfile.ZipFile(zip_path, "r") as archive:
        entries = []
        total_uncompressed = 0

        for info in archive.infolist():
            if info.is_dir():
                raise ArchiveError(
                    "bundle must not contain directory entries",
                    entry_name=info.filename,
                )

            normalized_name = _normalize_archive_name(info.filename)
            _validate_archive_name(normalized_name)
            _reject_symlink(info)

            if info.file_size > applied_limits["max_single_file_uncompressed_bytes"]:
                raise ArchiveError(
                    "bundle contains a file that exceeds the size limit",
                    entry_name=normalized_name,
                    file_size=info.file_size,
                )

            total_uncompressed += info.file_size
            entries.append(
                {
                    "name": normalized_name,
                    "original_name": info.filename,
                    "size": info.file_size,
                    "compressed_size": info.compress_size,
                }
            )

        if not entries:
            raise ArchiveError("bundle is empty")

        if len(entries) > applied_limits["max_files"]:
            raise ArchiveError(
                "bundle contains too many files",
                file_count=len(entries),
                max_files=applied_limits["max_files"],
            )

        if total_uncompressed > applied_limits["max_total_uncompressed_bytes"]:
            raise ArchiveError(
                "bundle exceeds total uncompressed size limit",
                total_uncompressed=total_uncompressed,
                max_total_uncompressed_bytes=applied_limits[
                    "max_total_uncompressed_bytes"
                ],
            )

        normalized_names = [entry["name"] for entry in entries]
        if len(set(normalized_names)) != len(normalized_names):
            raise ArchiveError(
                "bundle contains duplicate file names after normalization"
            )

        manifest_entries = [
            entry for entry in entries if entry["name"] == MANIFEST_FILENAME
        ]
        video_entries = [
            entry
            for entry in entries
            if os.path.splitext(entry["name"])[1].lower() in ALLOWED_VIDEO_EXTENSIONS
        ]

        if len(manifest_entries) != 1:
            raise ArchiveError(
                "bundle must contain exactly one maido.json file",
                manifest_count=len(manifest_entries),
            )

        if len(video_entries) != 1:
            raise ArchiveError(
                "bundle must contain exactly one supported video file",
                video_count=len(video_entries),
                allowed_extensions=sorted(ALLOWED_VIDEO_EXTENSIONS),
            )

        if len(entries) != 2:
            raise ArchiveError(
                "bundle must contain exactly one manifest and one video file",
                file_count=len(entries),
            )

        return {
            "bundle_path": str(zip_path),
            "entries": entries,
            "manifest_name": manifest_entries[0]["name"],
            "video_name": video_entries[0]["name"],
            "limits": applied_limits,
        }


def extract_validated_zip(zip_path, destination_dir, inspection=None):
    inspection = inspection or inspect_zip_file(zip_path)
    os.makedirs(destination_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        for entry in inspection["entries"]:
            source_name = entry["original_name"]
            target_name = entry["name"]
            target_path = os.path.join(destination_dir, target_name)
            with archive.open(source_name, "r") as source_handle:
                with open(target_path, "wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle)

    return {
        "manifest_path": os.path.join(destination_dir, inspection["manifest_name"]),
        "video_path": os.path.join(destination_dir, inspection["video_name"]),
        "video_name": inspection["video_name"],
        "manifest_name": inspection["manifest_name"],
    }


def _normalize_archive_name(name):
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _validate_archive_name(name):
    if not name:
        raise ArchiveError("bundle contains an empty file name")

    if name.startswith("/") or name.startswith("\\"):
        raise ArchiveError("bundle contains an absolute path", entry_name=name)

    if re.match(r"^[A-Za-z]:[/\\]", name):
        raise ArchiveError("bundle contains a drive-qualified path", entry_name=name)

    path = PurePosixPath(name)
    if ".." in path.parts:
        raise ArchiveError("bundle contains a path traversal entry", entry_name=name)

    if len(path.parts) != 1:
        raise ArchiveError(
            "bundle files must be stored at the archive root",
            entry_name=name,
        )


def _reject_symlink(info):
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise ArchiveError("bundle contains a symlink entry", entry_name=info.filename)
