from ..security.errors import CropConflictError


def plan_crop(
        source_width, source_height, cell_width, cell_height, center=None,
        min_dimensions=None, max_dimensions=None):
    source_width = _require_positive_number(source_width, "source_width")
    source_height = _require_positive_number(source_height, "source_height")
    cell_width = _require_positive_number(cell_width, "cell_width")
    cell_height = _require_positive_number(cell_height, "cell_height")

    target_aspect_ratio = cell_width / cell_height
    requested_center = _normalize_center(center, source_width, source_height)
    min_dimensions = _normalize_dimensions(min_dimensions)
    max_dimensions = _normalize_dimensions(max_dimensions)

    _validate_dimension_ranges(min_dimensions, max_dimensions)

    lower_width = 0.0
    upper_width = min(source_width, source_height * target_aspect_ratio)

    min_width = min_dimensions.get("width")
    min_height = min_dimensions.get("height")
    max_width = max_dimensions.get("width")
    max_height = max_dimensions.get("height")

    if min_width is not None:
        lower_width = max(lower_width, min_width)
    if min_height is not None:
        lower_width = max(lower_width, min_height * target_aspect_ratio)

    if max_width is not None:
        upper_width = min(upper_width, max_width)
    if max_height is not None:
        upper_width = min(upper_width, max_height * target_aspect_ratio)

    if lower_width > upper_width:
        raise CropConflictError(
            f"crop constraints cannot satisfy the target aspect ratio - {lower_width=} > {upper_width=}",
            source_width=source_width,
            source_height=source_height,
            cell_width=cell_width,
            cell_height=cell_height,
            min_dimensions=min_dimensions,
            max_dimensions=max_dimensions,
        )

    crop_width = upper_width
    crop_height = crop_width / target_aspect_ratio

    crop_x = _clamp(
        requested_center["x"] - (crop_width / 2.0), 0.0, source_width - crop_width
    )
    crop_y = _clamp(
        requested_center["y"] - (crop_height / 2.0), 0.0, source_height - crop_height
    )

    return {
        "source_width": source_width,
        "source_height": source_height,
        "cell_width": cell_width,
        "cell_height": cell_height,
        "target_aspect_ratio": target_aspect_ratio,
        "requested_center": requested_center,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "crop_width": crop_width,
        "crop_height": crop_height,
        "actual_center": {
            "x": crop_x + (crop_width / 2.0),
            "y": crop_y + (crop_height / 2.0),
        },
    }


def plan_crop_for_manifest(manifest, probe_info, cell_width, cell_height):
    return plan_crop(
        source_width=probe_info["width"],
        source_height=probe_info["height"],
        cell_width=cell_width,
        cell_height=cell_height,
        center=manifest.get("center"),
        min_dimensions=manifest.get("min_dimensions"),
        max_dimensions=manifest.get("max_dimensions"),
    )


def _normalize_center(center, source_width, source_height):
    if center is None:
        return {
            "x": source_width / 2.0,
            "y": source_height / 2.0,
        }

    if not isinstance(center, dict):
        raise CropConflictError("center must be an object when provided")
    if set(center.keys()) != {"x", "y"}:
        raise CropConflictError("center requires exactly x and y")

    x = _require_number(center["x"], "center.x")
    y = _require_number(center["y"], "center.y")

    if x < 0 or x > source_width:
        raise CropConflictError(
            "center.x must be within the source width",
            center_x=x,
            source_width=source_width,
        )
    if y < 0 or y > source_height:
        raise CropConflictError(
            "center.y must be within the source height",
            center_y=y,
            source_height=source_height,
        )

    return {"x": x, "y": y}


def _normalize_dimensions(dimensions):
    if dimensions is None:
        return {"width": None, "height": None}

    if not isinstance(dimensions, dict):
        raise CropConflictError("dimension constraints must be objects when provided")

    extra_keys = set(dimensions.keys()) - {"width", "height"}
    if extra_keys:
        raise CropConflictError(
            "dimension constraints only allow width and height",
            extra_keys=sorted(extra_keys),
        )

    width = _optional_positive_number(dimensions.get("width"), "width")
    height = _optional_positive_number(dimensions.get("height"), "height")

    if width is None and height is None:
        raise CropConflictError("dimension constraints require width or height")

    return {
        "width": width,
        "height": height,
    }


def _validate_dimension_ranges(min_dimensions, max_dimensions):
    if (
        min_dimensions.get("width") is not None
        and max_dimensions.get("width") is not None
        and min_dimensions["width"] > max_dimensions["width"]
    ):
        raise CropConflictError(
            "min_dimensions.width cannot exceed max_dimensions.width",
            min_width=min_dimensions["width"],
            max_width=max_dimensions["width"],
        )

    if (
        min_dimensions.get("height") is not None
        and max_dimensions.get("height") is not None
        and min_dimensions["height"] > max_dimensions["height"]
    ):
        raise CropConflictError(
            "min_dimensions.height cannot exceed max_dimensions.height",
            min_height=min_dimensions["height"],
            max_height=max_dimensions["height"],
        )


def _require_positive_number(value, field_name):
    number = _require_number(value, field_name)
    if number <= 0:
        raise CropConflictError(
            f"{field_name} must be greater than 0",
            field=field_name,
            actual_value=value,
        )
    return number


def _optional_positive_number(value, field_name):
    if value is None:
        return None

    number = _require_number(value, field_name)
    if number <= 0:
        raise CropConflictError(
            f"{field_name} must be greater than 0",
            field=field_name,
            actual_value=value,
        )
    return number


def _require_number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CropConflictError(f"{field_name} must be a number", field=field_name)
    return float(value)


def _clamp(value, minimum, maximum):
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value
