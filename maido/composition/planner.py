from ..crop import plan_crop_for_manifest
from ..layout import plan_layout
from ..security.errors import CompositionPlanError
from ..sync import plan_sync



def plan_composition(
        clips,
        core_input,
        canvas_width,
        canvas_height,
        layout_mode="horizontal",
        entry_fade_seconds=0.0,
        allow_size_override=False):
    normalized_clips = _normalize_composition_clips(clips)
    layout_clips = []
    for clip in normalized_clips:
        layout_clips.append(
            {
                "bundle_id": clip["bundle_id"],
                "preferred_direction": clip["manifest"].get("preferred_direction"),
                "min_dimensions": clip["manifest"].get("min_dimensions"),
                "max_dimensions": clip["manifest"].get("max_dimensions"),
            }
        )

    sync_plan = plan_sync(
        normalized_clips,
        core_input=core_input,
        entry_fade_seconds=entry_fade_seconds,
    )
    layout_plan = plan_layout(
        layout_clips,
        core_input=core_input,
        layout_mode=layout_mode,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        allow_size_override=allow_size_override,
    )
    clips_by_bundle_id = {}
    for clip in normalized_clips:
        clips_by_bundle_id[clip["bundle_id"]] = clip

    sync_by_bundle_id = {}
    for sync_entry in sync_plan["clips"]:
        sync_by_bundle_id[sync_entry["bundle_id"]] = sync_entry

    planned_clips = []
    for layout_entry in layout_plan:
        clip = clips_by_bundle_id[layout_entry["bundle_id"]]
        crop_plan = plan_crop_for_manifest(
            clip["manifest"],
            clip["probe"],
            layout_entry["cell_width"],
            layout_entry["cell_height"],
        )
        planned_clips.append(
            {
                "bundle_id": clip["bundle_id"],
                "input_index": layout_entry["input_index"],
                "role": layout_entry["role"],
                "source_path": clip["source_path"],
                "manifest": clip["manifest"],
                "probe": clip["probe"],
                "sync": sync_by_bundle_id[clip["bundle_id"]],
                "layout": layout_entry,
                "crop": crop_plan,
            }
        )

    return {
        "layout_mode": layout_mode,
        "core_input": core_input,
        "canvas_width": float(canvas_width),
        "canvas_height": float(canvas_height),
        "clip_count": len(planned_clips),
        "output_duration_seconds": sync_plan["output_duration_seconds"],
        "output_sync_point_seconds": sync_plan["output_sync_point_seconds"],
        "entry_fade_seconds": sync_plan["entry_fade_seconds"],
        "clips": planned_clips,
    }



def _normalize_composition_clips(clips):
    if not isinstance(clips, list) or not clips:
        raise CompositionPlanError("clips must be a non-empty list")

    normalized = []
    bundle_ids = set()
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise CompositionPlanError(
                "each composition clip must be an object",
                input_index=index,
            )

        bundle_id = clip.get("bundle_id")
        source_path = clip.get("source_path")
        manifest = clip.get("manifest")
        probe = clip.get("probe")

        if not isinstance(bundle_id, str) or not bundle_id.strip():
            raise CompositionPlanError(
                "each composition clip must include a non-empty bundle_id",
                input_index=index,
            )
        bundle_id = bundle_id.strip()
        if bundle_id in bundle_ids:
            raise CompositionPlanError(
                "composition clip bundle_id values must be unique",
                bundle_id=bundle_id,
            )
        bundle_ids.add(bundle_id)

        if not isinstance(manifest, dict):
            raise CompositionPlanError(
                "each composition clip must include a manifest object",
                bundle_id=bundle_id,
            )
        if not isinstance(probe, dict):
            raise CompositionPlanError(
                "each composition clip must include a probe object",
                bundle_id=bundle_id,
            )
        if "width" not in probe or "height" not in probe:
            raise CompositionPlanError(
                "probe must include width and height",
                bundle_id=bundle_id,
            )

        if source_path is not None:
            if not isinstance(source_path, str) or not source_path.strip():
                raise CompositionPlanError(
                    "source_path must be a non-empty string when provided",
                    bundle_id=bundle_id,
                )
            source_path = source_path.strip()

        normalized.append(
            {
                "bundle_id": bundle_id,
                "source_path": source_path,
                "manifest": manifest,
                "probe": probe,
            }
        )

    return normalized
