from ..security.errors import LayoutConflictError


ALLOWED_LAYOUT_MODES = {"horizontal", "vertical"}
ALLOWED_PREFERRED_DIRECTIONS = {"left", "right", "up", "down"}


def plan_layout(
        clips,
        core_input,
        layout_mode="horizontal",
        canvas_width=None,
        canvas_height=None):
    normalized_layout_mode = _normalize_layout_mode(layout_mode)
    normalized_clips = _normalize_clips(clips)
    clip_count = len(normalized_clips)
    normalized_core_input = _normalize_core_input(core_input, clip_count)
    _validate_canvas(canvas_width, canvas_height)
    _validate_axis_preferences(normalized_clips, normalized_core_input, normalized_layout_mode)

    core_cell_index = (clip_count - 1) // 2
    first_side_slots, second_side_slots = _build_side_slots(
        clip_count,
        core_cell_index,
        normalized_layout_mode,
    )
    supporting_clips = [
        clip
        for clip in normalized_clips
        if clip["input_index"] != normalized_core_input
    ]
    preferred_first, preferred_second = _group_supporting_clips(
        supporting_clips,
        normalized_layout_mode,
    )

    assignments = {
        normalized_core_input: core_cell_index,
    }
    remaining_first_slots = list(first_side_slots)
    remaining_second_slots = list(second_side_slots)

    for clip in preferred_first:
        if remaining_first_slots:
            assignments[clip["input_index"]] = remaining_first_slots.pop(0)

    for clip in preferred_second:
        if remaining_second_slots:
            assignments[clip["input_index"]] = remaining_second_slots.pop(0)

    remaining_slots = sorted(remaining_first_slots + remaining_second_slots)
    for clip in supporting_clips:
        if clip["input_index"] in assignments:
            continue
        if not remaining_slots:
            raise LayoutConflictError("layout planner ran out of slots unexpectedly")
        assignments[clip["input_index"]] = remaining_slots.pop(0)

    planned_entries = []
    for clip in normalized_clips:
        cell_index = assignments[clip["input_index"]]
        placement_direction = _resolve_placement_direction(
            normalized_layout_mode,
            cell_index,
            core_cell_index,
        )
        entry = {
            "bundle_id": clip["bundle_id"],
            "input_index": clip["input_index"],
            "role": "core" if clip["input_index"] == normalized_core_input else "supporting",
            "layout_mode": normalized_layout_mode,
            "cell_index": cell_index,
            "preferred_direction": clip["preferred_direction"],
            "placement_direction": placement_direction,
            "preference_satisfied": _is_preference_satisfied(
                clip["preferred_direction"],
                placement_direction,
            ),
        }
        if canvas_width is not None and canvas_height is not None:
            entry.update(
                _build_cell_geometry(
                    normalized_layout_mode,
                    clip_count,
                    cell_index,
                    canvas_width,
                    canvas_height,
                )
            )
        planned_entries.append(entry)

    return sorted(planned_entries, key=lambda entry: entry["cell_index"])


def _normalize_layout_mode(layout_mode):
    if not isinstance(layout_mode, str):
        raise LayoutConflictError("layout_mode must be a string")

    normalized = layout_mode.strip().lower()
    if normalized not in ALLOWED_LAYOUT_MODES:
        raise LayoutConflictError(
            "layout_mode must be horizontal or vertical",
            layout_mode=layout_mode,
        )
    return normalized


def _normalize_clips(clips):
    if not isinstance(clips, list) or not clips:
        raise LayoutConflictError("clips must be a non-empty list")

    normalized = []
    bundle_ids = set()
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise LayoutConflictError(
                "each clip must be an object",
                input_index=index,
            )

        bundle_id = clip.get("bundle_id")
        if not isinstance(bundle_id, str) or not bundle_id.strip():
            raise LayoutConflictError(
                "each clip must include a non-empty bundle_id",
                input_index=index,
            )
        bundle_id = bundle_id.strip()
        if bundle_id in bundle_ids:
            raise LayoutConflictError(
                "bundle_id values must be unique",
                bundle_id=bundle_id,
            )
        bundle_ids.add(bundle_id)

        preferred_direction = clip.get("preferred_direction")
        if preferred_direction is not None:
            if not isinstance(preferred_direction, str):
                raise LayoutConflictError(
                    "preferred_direction must be a string when provided",
                    bundle_id=bundle_id,
                )
            preferred_direction = preferred_direction.strip().lower()
            if preferred_direction not in ALLOWED_PREFERRED_DIRECTIONS:
                raise LayoutConflictError(
                    "preferred_direction must be one of left, right, up, down",
                    bundle_id=bundle_id,
                    preferred_direction=preferred_direction,
                )

        normalized.append(
            {
                "bundle_id": bundle_id,
                "input_index": index,
                "preferred_direction": preferred_direction,
            }
        )

    return normalized


def _normalize_core_input(core_input, clip_count):
    if isinstance(core_input, bool) or not isinstance(core_input, int):
        raise LayoutConflictError("core_input must be an integer index")
    if core_input < 0 or core_input >= clip_count:
        raise LayoutConflictError(
            "core_input is out of range",
            core_input=core_input,
            clip_count=clip_count,
        )
    return core_input


def _validate_canvas(canvas_width, canvas_height):
    if canvas_width is None and canvas_height is None:
        return
    if canvas_width is None or canvas_height is None:
        raise LayoutConflictError(
            "canvas_width and canvas_height must be provided together"
        )
    if canvas_width <= 0 or canvas_height <= 0:
        raise LayoutConflictError(
            "canvas_width and canvas_height must be greater than 0",
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )


def _validate_axis_preferences(clips, core_input, layout_mode):
    if layout_mode == "horizontal":
        allowed_directions = {"left", "right"}
        contradiction_message = (
            "horizontal layout only allows left or right preferred_direction"
        )
    else:
        allowed_directions = {"up", "down"}
        contradiction_message = (
            "vertical layout only allows up or down preferred_direction"
        )

    for clip in clips:
        if clip["input_index"] == core_input:
            continue
        preferred_direction = clip["preferred_direction"]
        if preferred_direction is None:
            continue
        if preferred_direction not in allowed_directions:
            raise LayoutConflictError(
                contradiction_message,
                bundle_id=clip["bundle_id"],
                preferred_direction=preferred_direction,
                layout_mode=layout_mode,
            )


def _build_side_slots(clip_count, core_cell_index, layout_mode):
    first_side_slots = list(range(0, core_cell_index))
    second_side_slots = list(range(core_cell_index + 1, clip_count))
    return first_side_slots, second_side_slots


def _group_supporting_clips(supporting_clips, layout_mode):
    if layout_mode == "horizontal":
        first_direction = "left"
        second_direction = "right"
    else:
        first_direction = "up"
        second_direction = "down"

    preferred_first = []
    preferred_second = []
    for clip in supporting_clips:
        if clip["preferred_direction"] == first_direction:
            preferred_first.append(clip)
        elif clip["preferred_direction"] == second_direction:
            preferred_second.append(clip)

    return preferred_first, preferred_second


def _resolve_placement_direction(layout_mode, cell_index, core_cell_index):
    if cell_index == core_cell_index:
        return "center"
    if layout_mode == "horizontal":
        return "left" if cell_index < core_cell_index else "right"
    return "up" if cell_index < core_cell_index else "down"


def _is_preference_satisfied(preferred_direction, placement_direction):
    if preferred_direction is None:
        return None
    return preferred_direction == placement_direction


def _build_cell_geometry(
        layout_mode,
        clip_count,
        cell_index,
        canvas_width,
        canvas_height):
    if layout_mode == "horizontal":
        cell_width = canvas_width / clip_count
        return {
            "cell_x": cell_index * cell_width,
            "cell_y": 0.0,
            "cell_width": cell_width,
            "cell_height": float(canvas_height),
        }

    cell_height = canvas_height / clip_count
    return {
        "cell_x": 0.0,
        "cell_y": cell_index * cell_height,
        "cell_width": float(canvas_width),
        "cell_height": cell_height,
    }
