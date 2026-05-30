from ..security.errors import RenderPlanError


ALLOWED_AUDIO_MODES = {"core", "mute", "file"}


def plan_render(
        composition_plan, audio_mode="core", audio_file=None,
        background_color=None):
    normalized_plan = _normalize_composition_plan(composition_plan)
    normalized_audio_mode = _normalize_audio_mode(audio_mode)
    normalized_audio_file = _normalize_audio_file(normalized_audio_mode, audio_file)
    normalized_background_color = _normalize_background_color(background_color)

    clip_instructions = []
    core_bundle_id = None
    for clip in normalized_plan["clips"]:
        source_path = clip.get("source_path")
        if not isinstance(source_path, str) or not source_path.strip():
            raise RenderPlanError(
                "each composition clip must include a non-empty source_path for render planning",
                bundle_id=clip.get("bundle_id"),
            )

        render_audio = normalized_audio_mode == "core" and clip["role"] == "core"
        if clip["role"] == "core":
            core_bundle_id = clip["bundle_id"]

        clip_instructions.append(
            {
                "bundle_id": clip["bundle_id"],
                "input_index": clip["input_index"],
                "role": clip["role"],
                "source_path": source_path.strip(),
                "trim_start_seconds": clip["sync"]["trim_start_seconds"],
                "trim_end_seconds": clip["sync"]["trim_end_seconds"],
                "output_start_seconds": clip["sync"]["output_start_seconds"],
                "output_end_seconds": clip["sync"]["output_end_seconds"],
                "visible_duration_seconds": clip["sync"]["visible_duration_seconds"],
                "leading_black_seconds": clip["sync"]["leading_black_seconds"],
                "trailing_black_seconds": clip["sync"]["trailing_black_seconds"],
                "applied_entry_fade_seconds": clip["sync"]["applied_entry_fade_seconds"],
                "crop_x": clip["crop"]["crop_x"],
                "crop_y": clip["crop"]["crop_y"],
                "crop_width": clip["crop"]["crop_width"],
                "crop_height": clip["crop"]["crop_height"],
                "cell_x": clip["layout"]["cell_x"],
                "cell_y": clip["layout"]["cell_y"],
                "cell_width": clip["layout"]["cell_width"],
                "cell_height": clip["layout"]["cell_height"],
                "placement_direction": clip["layout"]["placement_direction"],
                "preference_satisfied": clip["layout"]["preference_satisfied"],
                "render_audio": render_audio,
            }
        )

    if core_bundle_id is None:
        raise RenderPlanError("composition plan must contain exactly one core clip")

    return {
        "layout_mode": normalized_plan["layout_mode"],
        "canvas_width": normalized_plan["canvas_width"],
        "canvas_height": normalized_plan["canvas_height"],
        "output_duration_seconds": normalized_plan["output_duration_seconds"],
        "output_sync_point_seconds": normalized_plan["output_sync_point_seconds"],
        "background_color": normalized_background_color,
        "audio": {
            "mode": normalized_audio_mode,
            "core_bundle_id": core_bundle_id,
            "audio_file": normalized_audio_file,
        },
        "clips": clip_instructions,
    }



def _normalize_composition_plan(composition_plan):
    if not isinstance(composition_plan, dict):
        raise RenderPlanError("composition_plan must be an object")

    required_fields = {
        "layout_mode",
        "canvas_width",
        "canvas_height",
        "output_duration_seconds",
        "output_sync_point_seconds",
        "clips",
    }
    missing_fields = sorted(required_fields - set(composition_plan.keys()))
    if missing_fields:
        raise RenderPlanError(
            "composition_plan is missing required fields",
            missing_fields=missing_fields,
        )

    clips = composition_plan["clips"]
    if not isinstance(clips, list) or not clips:
        raise RenderPlanError("composition_plan.clips must be a non-empty list")

    return composition_plan



def _normalize_audio_mode(audio_mode):
    if not isinstance(audio_mode, str):
        raise RenderPlanError("audio_mode must be a string")

    normalized = audio_mode.strip().lower()
    if normalized not in ALLOWED_AUDIO_MODES:
        raise RenderPlanError(
            "audio_mode must be core, mute, or file",
            audio_mode=audio_mode,
        )
    return normalized



def _normalize_audio_file(audio_mode, audio_file):
    if audio_mode == "file":
        if not isinstance(audio_file, str) or not audio_file.strip():
            raise RenderPlanError(
                "audio_file is required when audio_mode is file",
                audio_mode=audio_mode,
            )
        return audio_file.strip()

    if audio_file is not None:
        raise RenderPlanError(
            "audio_file may only be provided when audio_mode is file",
            audio_mode=audio_mode,
        )
    return None



def _normalize_background_color(background_color):
    if background_color is None:
        return "black"

    if isinstance(background_color, str):
        if not background_color.strip():
            raise RenderPlanError("background_color must not be empty")
        return background_color.strip()

    if isinstance(background_color, (list, tuple)) and len(background_color) == 3:
        normalized = []
        for index, value in enumerate(background_color):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RenderPlanError(
                    "background_color RGB values must be numbers",
                    field=f"background_color[{index}]",
                )
            if value < 0 or value > 255:
                raise RenderPlanError(
                    "background_color RGB values must be between 0 and 255",
                    field=f"background_color[{index}]",
                    actual_value=value,
                )
            normalized.append(float(value))
        return tuple(normalized)

    raise RenderPlanError(
        "background_color must be a color string or an RGB triple"
    )
