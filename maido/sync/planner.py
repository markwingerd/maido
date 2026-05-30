from ..security.errors import SyncConflictError



def plan_sync(
        clips,
        core_input,
        entry_fade_seconds=0.0):
    normalized_clips = _normalize_sync_clips(clips)
    clip_count = len(normalized_clips)
    normalized_core_input = _normalize_core_input(core_input, clip_count)
    normalized_entry_fade_seconds = _normalize_non_negative_number(
        entry_fade_seconds,
        "entry_fade_seconds",
    )

    core_clip = normalized_clips[normalized_core_input]
    core_sync_point_seconds = _get_sync_point_seconds(core_clip)
    output_duration_seconds = _get_duration_seconds(core_clip)

    planned_entries = []
    for clip in normalized_clips:
        clip_sync_point_seconds = _get_sync_point_seconds(clip)
        clip_duration_seconds = _get_duration_seconds(clip)
        sync_offset_seconds = core_sync_point_seconds - clip_sync_point_seconds

        if clip["input_index"] == normalized_core_input:
            trim_start_seconds = 0.0
            output_start_seconds = 0.0
        elif sync_offset_seconds >= 0:
            trim_start_seconds = 0.0
            output_start_seconds = sync_offset_seconds
        else:
            trim_start_seconds = -sync_offset_seconds
            output_start_seconds = 0.0

        available_duration_seconds = max(
            0.0,
            clip_duration_seconds - trim_start_seconds,
        )
        visible_duration_seconds = min(
            available_duration_seconds,
            max(0.0, output_duration_seconds - output_start_seconds),
        )
        output_end_seconds = output_start_seconds + visible_duration_seconds
        trim_end_seconds = trim_start_seconds + visible_duration_seconds
        leading_black_seconds = output_start_seconds
        trailing_black_seconds = max(0.0, output_duration_seconds - output_end_seconds)
        applied_entry_fade_seconds = 0.0
        if (
            clip["input_index"] != normalized_core_input
            and output_start_seconds > 0
            and visible_duration_seconds > 0
        ):
            applied_entry_fade_seconds = min(
                normalized_entry_fade_seconds,
                visible_duration_seconds,
            )

        planned_entries.append(
            {
                "bundle_id": clip["bundle_id"],
                "input_index": clip["input_index"],
                "role": "core" if clip["input_index"] == normalized_core_input else "supporting",
                "source_duration_seconds": clip_duration_seconds,
                "source_sync_point_seconds": clip_sync_point_seconds,
                "output_sync_point_seconds": core_sync_point_seconds,
                "output_duration_seconds": output_duration_seconds,
                "sync_offset_seconds": sync_offset_seconds,
                "trim_start_seconds": trim_start_seconds,
                "trim_end_seconds": trim_end_seconds,
                "output_start_seconds": output_start_seconds,
                "output_end_seconds": output_end_seconds,
                "leading_black_seconds": leading_black_seconds,
                "trailing_black_seconds": trailing_black_seconds,
                "visible_duration_seconds": visible_duration_seconds,
                "applied_entry_fade_seconds": applied_entry_fade_seconds,
                "starts_with_black": leading_black_seconds > 0,
                "ends_with_black": trailing_black_seconds > 0,
            }
        )

    return {
        "core_input": normalized_core_input,
        "output_duration_seconds": output_duration_seconds,
        "output_sync_point_seconds": core_sync_point_seconds,
        "entry_fade_seconds": normalized_entry_fade_seconds,
        "clips": planned_entries,
    }



def _normalize_sync_clips(clips):
    if not isinstance(clips, list) or not clips:
        raise SyncConflictError("clips must be a non-empty list")

    normalized = []
    bundle_ids = set()
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise SyncConflictError(
                "each sync clip must be an object",
                input_index=index,
            )

        bundle_id = clip.get("bundle_id")
        manifest = clip.get("manifest")
        probe = clip.get("probe")

        if not isinstance(bundle_id, str) or not bundle_id.strip():
            raise SyncConflictError(
                "each sync clip must include a non-empty bundle_id",
                input_index=index,
            )
        bundle_id = bundle_id.strip()
        if bundle_id in bundle_ids:
            raise SyncConflictError(
                "sync clip bundle_id values must be unique",
                bundle_id=bundle_id,
            )
        bundle_ids.add(bundle_id)

        if not isinstance(manifest, dict):
            raise SyncConflictError(
                "each sync clip must include a manifest object",
                bundle_id=bundle_id,
            )
        if not isinstance(probe, dict):
            raise SyncConflictError(
                "each sync clip must include a probe object",
                bundle_id=bundle_id,
            )

        normalized.append(
            {
                "bundle_id": bundle_id,
                "input_index": index,
                "manifest": manifest,
                "probe": probe,
            }
        )

    return normalized



def _normalize_core_input(core_input, clip_count):
    if isinstance(core_input, bool) or not isinstance(core_input, int):
        raise SyncConflictError("core_input must be an integer index")
    if core_input < 0 or core_input >= clip_count:
        raise SyncConflictError(
            "core_input is out of range",
            core_input=core_input,
            clip_count=clip_count,
        )
    return core_input



def _get_sync_point_seconds(clip):
    sync_point_seconds = clip["manifest"].get("sync_point_seconds")
    if isinstance(sync_point_seconds, bool) or not isinstance(sync_point_seconds, (int, float)):
        raise SyncConflictError(
            "manifest must include numeric sync_point_seconds",
            bundle_id=clip["bundle_id"],
        )
    if sync_point_seconds < 0:
        raise SyncConflictError(
            "sync_point_seconds must be greater than or equal to 0",
            bundle_id=clip["bundle_id"],
            sync_point_seconds=sync_point_seconds,
        )
    return float(sync_point_seconds)



def _get_duration_seconds(clip):
    duration_seconds = clip["probe"].get("duration_seconds")
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float)):
        raise SyncConflictError(
            "probe must include numeric duration_seconds",
            bundle_id=clip["bundle_id"],
        )
    if duration_seconds < 0:
        raise SyncConflictError(
            "duration_seconds must be greater than or equal to 0",
            bundle_id=clip["bundle_id"],
            duration_seconds=duration_seconds,
        )
    return float(duration_seconds)



def _normalize_non_negative_number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SyncConflictError(f"{field_name} must be a number", field=field_name)
    if value < 0:
        raise SyncConflictError(
            f"{field_name} must be greater than or equal to 0",
            field=field_name,
            actual_value=value,
        )
    return float(value)
