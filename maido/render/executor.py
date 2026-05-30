import importlib

from ..security.errors import RenderExecutionError


DEFAULT_RENDER_FPS = 30.0
NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
}


def render_plan_to_file(
        render_plan, output_path, fps=None, codec="libx264",
        audio_codec="aac", moviepy_api=None):
    normalized_plan = _normalize_render_plan(render_plan)
    normalized_output_path = _normalize_non_empty_string(output_path, "output_path")
    normalized_fps = _normalize_optional_positive_number(fps, "fps")
    normalized_codec = _normalize_non_empty_string(codec, "codec")
    normalized_audio_codec = _normalize_non_empty_string(audio_codec, "audio_codec")
    api = moviepy_api or _load_moviepy_api()
    background_color = _coerce_background_color(normalized_plan["background_color"])
    canvas_size = (
        int(round(normalized_plan["canvas_width"])),
        int(round(normalized_plan["canvas_height"])),
    )
    output_duration_seconds = normalized_plan["output_duration_seconds"]
    effective_fps = normalized_fps or DEFAULT_RENDER_FPS

    managed_clips = []
    composite_clip = None
    external_audio_clip = None
    try:
        background_clip = api.ColorClip(canvas_size, color=background_color)
        background_clip = background_clip.set_duration(output_duration_seconds)
        managed_clips.append(background_clip)
        video_layers = [background_clip]

        for instruction in normalized_plan["clips"]:
            source_clip = api.VideoFileClip(instruction["source_path"])
            managed_clips.append(source_clip)
            layer_clip = source_clip.subclip(
                instruction["trim_start_seconds"],
                instruction["trim_end_seconds"],
            )
            managed_clips.append(layer_clip)
            layer_clip = layer_clip.crop(
                x1=instruction["crop_x"],
                y1=instruction["crop_y"],
                x2=instruction["crop_x"] + instruction["crop_width"],
                y2=instruction["crop_y"] + instruction["crop_height"],
            )
            layer_clip = layer_clip.resize(
                newsize=(
                    int(round(instruction["cell_width"])),
                    int(round(instruction["cell_height"])),
                )
            )
            if instruction["applied_entry_fade_seconds"] > 0:
                layer_clip = layer_clip.fx(
                    api.vfx.fadein,
                    instruction["applied_entry_fade_seconds"],
                )
            layer_clip = layer_clip.set_start(instruction["output_start_seconds"])
            layer_clip = layer_clip.set_position(
                (instruction["cell_x"], instruction["cell_y"])
            )
            if not instruction["render_audio"]:
                layer_clip = _remove_audio(layer_clip)
            video_layers.append(layer_clip)
            managed_clips.append(layer_clip)

        composite_clip = api.CompositeVideoClip(video_layers, size=canvas_size)
        composite_clip = composite_clip.set_duration(output_duration_seconds)

        if normalized_plan["audio"]["mode"] == "mute":
            composite_clip = _remove_audio(composite_clip)
        elif normalized_plan["audio"]["mode"] == "file":
            external_audio_clip = api.AudioFileClip(normalized_plan["audio"]["audio_file"])
            managed_clips.append(external_audio_clip)
            audio_duration_seconds = getattr(external_audio_clip, "duration", None)
            if (
                isinstance(audio_duration_seconds, (int, float))
                and audio_duration_seconds > output_duration_seconds
            ):
                external_audio_clip = external_audio_clip.subclip(0, output_duration_seconds)
            composite_clip = composite_clip.set_audio(external_audio_clip)

        composite_clip.write_videofile(
            normalized_output_path,
            fps=effective_fps,
            codec=normalized_codec,
            audio_codec=normalized_audio_codec,
        )
    except RenderExecutionError:
        raise
    except Exception as error:
        raise RenderExecutionError(
            "render execution failed",
            error_type=error.__class__.__name__,
            output_path=normalized_output_path,
        ) from error
    finally:
        if composite_clip is not None:
            _close_if_possible(composite_clip)
        if external_audio_clip is not None:
            _close_if_possible(external_audio_clip)
        for clip in reversed(managed_clips):
            _close_if_possible(clip)

    return {
        "output_path": normalized_output_path,
        "fps": effective_fps,
        "codec": normalized_codec,
        "audio_codec": normalized_audio_codec,
        "audio_mode": normalized_plan["audio"]["mode"],
        "clip_count": len(normalized_plan["clips"]),
    }



def _load_moviepy_api():
    try:
        editor = importlib.import_module("moviepy.editor")
        vfx = importlib.import_module("moviepy.video.fx.all")
    except ImportError as error:
        raise RenderExecutionError(
            "moviepy is not installed; install project dependencies before rendering"
        ) from error

    return _MoviePyApi(
        ColorClip=editor.ColorClip,
        VideoFileClip=editor.VideoFileClip,
        CompositeVideoClip=editor.CompositeVideoClip,
        AudioFileClip=editor.AudioFileClip,
        vfx=vfx,
    )



def _normalize_render_plan(render_plan):
    if not isinstance(render_plan, dict):
        raise RenderExecutionError("render_plan must be an object")

    required_fields = {
        "canvas_width",
        "canvas_height",
        "output_duration_seconds",
        "background_color",
        "audio",
        "clips",
    }
    missing_fields = sorted(required_fields - set(render_plan.keys()))
    if missing_fields:
        raise RenderExecutionError(
            "render_plan is missing required fields",
            missing_fields=missing_fields,
        )

    if not isinstance(render_plan["clips"], list) or not render_plan["clips"]:
        raise RenderExecutionError("render_plan.clips must be a non-empty list")

    if not isinstance(render_plan["audio"], dict):
        raise RenderExecutionError("render_plan.audio must be an object")

    return render_plan



def _normalize_optional_positive_number(value, field_name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RenderExecutionError(f"{field_name} must be a number", field=field_name)
    if value <= 0:
        raise RenderExecutionError(
            f"{field_name} must be greater than 0",
            field=field_name,
            actual_value=value,
        )
    return float(value)



def _normalize_non_empty_string(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise RenderExecutionError(
            f"{field_name} must be a non-empty string",
            field=field_name,
        )
    return value.strip()



def _coerce_background_color(background_color):
    if isinstance(background_color, str):
        normalized = background_color.strip().lower()
        if normalized in NAMED_COLORS:
            return NAMED_COLORS[normalized]
        if normalized.startswith("#") and len(normalized) == 7:
            return (
                int(normalized[1:3], 16),
                int(normalized[3:5], 16),
                int(normalized[5:7], 16),
            )
        raise RenderExecutionError(
            "unsupported background color string",
            background_color=background_color,
        )

    if isinstance(background_color, (list, tuple)) and len(background_color) == 3:
        return tuple(int(round(value)) for value in background_color)

    raise RenderExecutionError("background_color must be a color string or RGB triple")



def _remove_audio(clip):
    if hasattr(clip, "without_audio"):
        return clip.without_audio()
    if hasattr(clip, "set_audio"):
        return clip.set_audio(None)
    return clip



def _close_if_possible(resource):
    if hasattr(resource, "close"):
        resource.close()


class _MoviePyApi:
    def __init__(self, ColorClip, VideoFileClip, CompositeVideoClip, AudioFileClip, vfx):
        self.ColorClip = ColorClip
        self.VideoFileClip = VideoFileClip
        self.CompositeVideoClip = CompositeVideoClip
        self.AudioFileClip = AudioFileClip
        self.vfx = vfx
