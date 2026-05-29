import json

from ..security.errors import ManifestParseError, ManifestValidationError

ALLOWED_PREFERRED_DIRECTIONS = {
    "left",
    "right",
    "up",
    "down",
}
KNOWN_TOP_LEVEL_FIELDS = {
    "version",
    "video_file",
    "sync_point_seconds",
    "label",
    "center",
    "min_dimensions",
    "max_dimensions",
    "preferred_direction",
    "notes",
    "tags",
}


def load_manifest_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as error:
        raise ManifestParseError(
            "manifest is not valid JSON",
            path=str(path),
            line=error.lineno,
            column=error.colno,
        ) from error


def validate_manifest(data):
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be a JSON object")

    version = _require_string(data, "version")
    if version != "1":
        raise ManifestValidationError(
            "version must be '1'",
            field="version",
            actual_value=version,
        )

    video_file = _require_string(data, "video_file")
    sync_point_seconds = _require_number(data, "sync_point_seconds", minimum=0)

    label = _optional_string(data, "label")
    center = _validate_center(data.get("center"))
    min_dimensions = _validate_dimension_object(
        data.get("min_dimensions"),
        "min_dimensions",
    )
    max_dimensions = _validate_dimension_object(
        data.get("max_dimensions"),
        "max_dimensions",
    )
    _validate_dimension_ranges(min_dimensions, max_dimensions)
    preferred_direction = _validate_preferred_direction(data.get("preferred_direction"))
    notes = _optional_string(data, "notes")
    tags = _validate_tags(data.get("tags"))
    unknown_fields = sorted(set(data.keys()) - KNOWN_TOP_LEVEL_FIELDS)

    return {
        "version": version,
        "video_file": video_file,
        "sync_point_seconds": float(sync_point_seconds),
        "label": label,
        "center": center,
        "min_dimensions": min_dimensions,
        "max_dimensions": max_dimensions,
        "preferred_direction": preferred_direction,
        "notes": notes,
        "tags": tags,
        "warnings": _build_warnings(unknown_fields),
    }


def validate_manifest_against_probe(manifest, probe_info):
    duration = probe_info["duration_seconds"]
    width = probe_info["width"]
    height = probe_info["height"]

    if manifest["sync_point_seconds"] > duration:
        raise ManifestValidationError(
            "sync_point_seconds exceeds source duration",
            field="sync_point_seconds",
            sync_point_seconds=manifest["sync_point_seconds"],
            source_duration=duration,
        )

    center = manifest.get("center")
    if center:
        if center["x"] < 0 or center["x"] > width:
            raise ManifestValidationError(
                "center.x must be within source width",
                field="center.x",
                center_x=center["x"],
                source_width=width,
            )
        if center["y"] < 0 or center["y"] > height:
            raise ManifestValidationError(
                "center.y must be within source height",
                field="center.y",
                center_y=center["y"],
                source_height=height,
            )

    _validate_dimensions_against_probe(
        manifest.get("min_dimensions"),
        "min_dimensions",
        width,
        height,
    )
    _validate_dimensions_against_probe(
        manifest.get("max_dimensions"),
        "max_dimensions",
        width,
        height,
    )

    return manifest


def _require_string(data, field_name):
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(
            f"{field_name} must be a non-empty string",
            field=field_name,
        )
    return value.strip()


def _optional_string(data, field_name):
    if field_name not in data or data[field_name] is None:
        return None

    value = data[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(
            f"{field_name} must be a non-empty string when provided",
            field=field_name,
        )
    return value.strip()


def _require_number(data, field_name, minimum=None):
    value = data.get(field_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestValidationError(
            f"{field_name} must be a number",
            field=field_name,
        )
    if minimum is not None and value < minimum:
        raise ManifestValidationError(
            f"{field_name} must be greater than or equal to {minimum}",
            field=field_name,
            minimum=minimum,
            actual_value=value,
        )
    return value


def _validate_center(value):
    if value is None:
        return None

    if not isinstance(value, dict):
        raise ManifestValidationError("center must be an object", field="center")

    if set(value.keys()) != {"x", "y"}:
        raise ManifestValidationError(
            "center requires exactly x and y",
            field="center",
        )

    x = _require_nested_number(value, "center", "x")
    y = _require_nested_number(value, "center", "y")
    return {"x": float(x), "y": float(y)}


def _validate_dimension_object(value, field_name):
    if value is None:
        return None

    if not isinstance(value, dict):
        raise ManifestValidationError(
            f"{field_name} must be an object",
            field=field_name,
        )

    allowed_keys = {"width", "height"}
    extra_keys = set(value.keys()) - allowed_keys
    if extra_keys:
        raise ManifestValidationError(
            f"{field_name} only allows width and height",
            field=field_name,
            extra_keys=sorted(extra_keys),
        )

    width = _optional_nested_number(value, field_name, "width", minimum=0)
    height = _optional_nested_number(value, field_name, "height", minimum=0)

    if width is None and height is None:
        raise ManifestValidationError(
            f"{field_name} requires width or height",
            field=field_name,
        )

    return {
        "width": width,
        "height": height,
    }


def _validate_dimension_ranges(min_dimensions, max_dimensions):
    if not min_dimensions or not max_dimensions:
        return

    if (
        min_dimensions.get("width") is not None
        and max_dimensions.get("width") is not None
        and min_dimensions["width"] > max_dimensions["width"]
    ):
        raise ManifestValidationError(
            "min_dimensions.width cannot exceed max_dimensions.width",
            field="min_dimensions.width",
            min_width=min_dimensions["width"],
            max_width=max_dimensions["width"],
        )

    if (
        min_dimensions.get("height") is not None
        and max_dimensions.get("height") is not None
        and min_dimensions["height"] > max_dimensions["height"]
    ):
        raise ManifestValidationError(
            "min_dimensions.height cannot exceed max_dimensions.height",
            field="min_dimensions.height",
            min_height=min_dimensions["height"],
            max_height=max_dimensions["height"],
        )


def _validate_dimensions_against_probe(
    dimensions, field_name, source_width, source_height
):
    if not dimensions:
        return

    if dimensions.get("width") is not None and dimensions["width"] > source_width:
        raise ManifestValidationError(
            f"{field_name}.width exceeds source width",
            field=f"{field_name}.width",
            requested_width=dimensions["width"],
            source_width=source_width,
        )
    if dimensions.get("height") is not None and dimensions["height"] > source_height:
        raise ManifestValidationError(
            f"{field_name}.height exceeds source height",
            field=f"{field_name}.height",
            requested_height=dimensions["height"],
            source_height=source_height,
        )


def _validate_preferred_direction(value):
    if value is None:
        return None

    if not isinstance(value, str):
        raise ManifestValidationError(
            "preferred_direction must be a string",
            field="preferred_direction",
        )

    normalized = value.strip().lower()
    if normalized not in ALLOWED_PREFERRED_DIRECTIONS:
        raise ManifestValidationError(
            "preferred_direction must be one of left, right, up, down",
            field="preferred_direction",
            actual_value=value,
        )

    return normalized


def _validate_tags(value):
    if value is None:
        return []

    if not isinstance(value, list):
        raise ManifestValidationError("tags must be an array", field="tags")

    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ManifestValidationError(
                "tags must only contain non-empty strings",
                field=f"tags[{index}]",
            )
        normalized.append(item.strip())

    return normalized


def _require_nested_number(data, parent_name, field_name):
    value = data.get(field_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestValidationError(
            f"{parent_name}.{field_name} must be a number",
            field=f"{parent_name}.{field_name}",
        )
    return value


def _optional_nested_number(data, parent_name, field_name, minimum=None):
    if field_name not in data or data[field_name] is None:
        return None

    value = data[field_name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestValidationError(
            f"{parent_name}.{field_name} must be a number",
            field=f"{parent_name}.{field_name}",
        )
    if minimum is not None and value <= minimum:
        raise ManifestValidationError(
            f"{parent_name}.{field_name} must be greater than {minimum}",
            field=f"{parent_name}.{field_name}",
            actual_value=value,
        )
    return float(value)


def _build_warnings(unknown_fields):
    warnings = []
    for field_name in unknown_fields:
        warnings.append(f"unknown manifest field ignored: {field_name}")
    return warnings
