from ..security.errors import LayoutConflictError


ALLOWED_LAYOUT_MODES = {"horizontal", "vertical"}
ALLOWED_PREFERRED_DIRECTIONS = {"left", "right", "up", "down"}
EPSILON = 0.000001  # Used to avoid **float-comparison edge cases.


def plan_layout(
        clips, core_input, layout_mode="horizontal", canvas_width=None,
        canvas_height=None, allow_size_override=False):
    normalized_layout_mode = _normalize_layout_mode(layout_mode)
    normalized_clips = _normalize_clips(clips)
    clip_count = len(normalized_clips)
    normalized_core_input = _normalize_core_input(core_input, clip_count)
    _validate_canvas(canvas_width, canvas_height)
    _validate_axis_preferences(
        normalized_clips,
        normalized_core_input,
        normalized_layout_mode,
    )

    core_cell_index = (clip_count - 1) // 2
    first_side_slots, second_side_slots = _build_side_slots(clip_count, core_cell_index)
    supporting_clips = [
        clip
        for clip in normalized_clips
        if clip["input_index"] != normalized_core_input
    ]
    preferred_first, preferred_second = _group_supporting_clips(
        supporting_clips,
        normalized_layout_mode,
    )

    assignments = {normalized_core_input: core_cell_index}
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
            "min_dimensions": clip["min_dimensions"],
            "max_dimensions": clip["max_dimensions"],
        }
        planned_entries.append(entry)

    planned_entries = sorted(planned_entries, key=lambda entry: entry["cell_index"])
    if canvas_width is not None and canvas_height is not None:
        sized_entries = _apply_cell_geometry(
            planned_entries,
            normalized_layout_mode,
            float(canvas_width),
            float(canvas_height),
            allow_size_override,
        )
        return sized_entries

    return planned_entries



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

        min_dimensions = _normalize_dimension_object(clip.get("min_dimensions"))
        max_dimensions = _normalize_dimension_object(clip.get("max_dimensions"))

        normalized.append(
            {
                "bundle_id": bundle_id,
                "input_index": index,
                "preferred_direction": preferred_direction,
                "min_dimensions": min_dimensions,
                "max_dimensions": max_dimensions,
            }
        )

    return normalized



def _normalize_dimension_object(dimensions):
    if dimensions is None:
        return {"width": None, "height": None}
    if not isinstance(dimensions, dict):
        raise LayoutConflictError("dimension constraints must be objects when provided")

    extra_keys = set(dimensions.keys()) - {"width", "height"}
    if extra_keys:
        raise LayoutConflictError(
            "dimension constraints only allow width and height",
            extra_keys=sorted(extra_keys),
        )

    width = _normalize_dimension_value(dimensions.get("width"), "width")
    height = _normalize_dimension_value(dimensions.get("height"), "height")
    return {"width": width, "height": height}



def _normalize_dimension_value(value, field_name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LayoutConflictError(
            f"{field_name} must be a number when provided",
            field=field_name,
        )
    if value <= 0:
        raise LayoutConflictError(
            f"{field_name} must be greater than 0 when provided",
            field=field_name,
            actual_value=value,
        )
    return float(value)



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



def _build_side_slots(clip_count, core_cell_index):
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



def _apply_cell_geometry(
        planned_entries, layout_mode, canvas_width, canvas_height,
        allow_size_override):
    axis_key = "width" if layout_mode == "horizontal" else "height"
    canvas_axis_size = canvas_width if layout_mode == "horizontal" else canvas_height
    core_index = None
    minimum_sizes = []
    maximum_sizes = []

    for index, entry in enumerate(planned_entries):
        if entry["role"] == "core":
            core_index = index
        minimum_size = entry["min_dimensions"].get(axis_key) or 0.0
        maximum_size = entry["max_dimensions"].get(axis_key)
        minimum_sizes.append(float(minimum_size))
        maximum_sizes.append(None if maximum_size is None else float(maximum_size))

    if core_index is None:
        raise LayoutConflictError("layout plan must contain exactly one core clip")

    axis_sizes = _allocate_axis_sizes(
        minimum_sizes,
        maximum_sizes,
        core_index,
        canvas_axis_size,
        allow_size_override,
        layout_mode,
    )
    occupied_axis_size = sum(axis_sizes)
    axis_offset = max(0.0, (canvas_axis_size - occupied_axis_size) / 2.0)
    cursor = axis_offset

    sized_entries = []
    for entry, axis_size in zip(planned_entries, axis_sizes):
        sized_entry = dict(entry)
        if layout_mode == "horizontal":
            sized_entry.update(
                {
                    "cell_x": cursor,
                    "cell_y": 0.0,
                    "cell_width": axis_size,
                    "cell_height": canvas_height,
                }
            )
        else:
            sized_entry.update(
                {
                    "cell_x": 0.0,
                    "cell_y": cursor,
                    "cell_width": canvas_width,
                    "cell_height": axis_size,
                }
            )
        cursor += axis_size
        sized_entries.append(sized_entry)

    return sized_entries



def _allocate_axis_sizes(
        minimum_sizes, maximum_sizes, core_index, canvas_axis_size,
        allow_size_override, layout_mode):
    total_minimum_size = sum(minimum_sizes)
    total_maximum_size = _sum_defined_maximum_sizes(maximum_sizes)

    if total_minimum_size > canvas_axis_size + EPSILON:
        if not allow_size_override:
            raise LayoutConflictError(
                _build_minimum_overflow_message(
                    layout_mode,
                    total_minimum_size,
                    canvas_axis_size,
                ),
                total_minimum_size=total_minimum_size,
                canvas_axis_size=canvas_axis_size,
                hint="pass allow_size_override=True or use the CLI overwrite-size flag",
            )
        return _allocate_with_core_priority(
            minimum_sizes,
            core_index,
            canvas_axis_size,
            layout_mode,
        )

    sizes = list(minimum_sizes)
    remaining = canvas_axis_size - total_minimum_size
    expandable = [
        index
        for index, maximum_size in enumerate(maximum_sizes)
        if maximum_size is None or maximum_size - sizes[index] > EPSILON
    ]

    while remaining > EPSILON and expandable:
        share = remaining / len(expandable)
        next_expandable = []
        consumed = 0.0
        for index in expandable:
            maximum_size = maximum_sizes[index]
            if maximum_size is None:
                delta = share
            else:
                delta = min(share, maximum_size - sizes[index])
            sizes[index] += delta
            consumed += delta
            if maximum_size is None or maximum_size - sizes[index] > EPSILON:
                next_expandable.append(index)
        if consumed <= EPSILON:
            break
        remaining -= consumed
        expandable = next_expandable

    if total_maximum_size is not None and total_maximum_size < canvas_axis_size - EPSILON:
        return sizes

    return sizes



def _allocate_with_core_priority(
        minimum_sizes, core_index, canvas_axis_size, layout_mode):
    core_minimum_size = minimum_sizes[core_index]
    if core_minimum_size > canvas_axis_size + EPSILON:
        raise LayoutConflictError(
            _build_core_overflow_message(layout_mode, core_minimum_size, canvas_axis_size),
            core_minimum_size=core_minimum_size,
            canvas_axis_size=canvas_axis_size,
        )

    sizes = [0.0 for _ in minimum_sizes]
    sizes[core_index] = core_minimum_size
    remaining = canvas_axis_size - core_minimum_size
    support_indices = [index for index in range(len(minimum_sizes)) if index != core_index]
    if not support_indices or remaining <= EPSILON:
        return sizes

    support_total_minimum = sum(minimum_sizes[index] for index in support_indices)
    if support_total_minimum > EPSILON:
        for index in support_indices:
            sizes[index] = remaining * (minimum_sizes[index] / support_total_minimum)
    else:
        share = remaining / len(support_indices)
        for index in support_indices:
            sizes[index] = share
    return sizes



def _sum_defined_maximum_sizes(maximum_sizes):
    total = 0.0
    for maximum_size in maximum_sizes:
        if maximum_size is None:
            return None
        total += maximum_size
    return total



def _build_minimum_overflow_message(
        layout_mode, total_minimum_size, canvas_axis_size):
    axis_name = "width" if layout_mode == "horizontal" else "height"
    return (
        f"combined minimum {axis_name}s ({total_minimum_size:.3f}) exceed the "
        f"available canvas {axis_name} ({canvas_axis_size:.3f})"
    )



def _build_core_overflow_message(layout_mode, core_minimum_size, canvas_axis_size):
    axis_name = "width" if layout_mode == "horizontal" else "height"
    return (
        f"core minimum {axis_name} ({core_minimum_size:.3f}) exceeds the "
        f"available canvas {axis_name} ({canvas_axis_size:.3f})"
    )
