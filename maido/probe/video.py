import importlib

from maido.security.errors import VideoProbeError


def probe_video_file(path):
    try:
        reader_module = importlib.import_module("moviepy.video.io.ffmpeg_reader")
        ffmpeg_parse_infos = reader_module.ffmpeg_parse_infos
    except ImportError as error:
        raise VideoProbeError(
            "moviepy is not installed; install project dependencies before probing video files"
        ) from error

    try:
        info = ffmpeg_parse_infos(str(path), check_duration=True)
    except Exception as error:
        raise VideoProbeError(
            "failed to probe video file",
            source_path=str(path),
            error_type=error.__class__.__name__,
        ) from error

    video_size = info.get("video_size")
    duration = info.get("duration")
    fps = info.get("video_fps")

    if not video_size or len(video_size) != 2:
        raise VideoProbeError(
            "video probe did not return a valid frame size",
            source_path=str(path),
        )

    if duration is None:
        raise VideoProbeError(
            "video probe did not return a duration",
            source_path=str(path),
        )

    return {
        "width": int(video_size[0]),
        "height": int(video_size[1]),
        "duration_seconds": float(duration),
        "fps": float(fps) if fps is not None else None,
    }
