from contextlib import ExitStack

from ..bundle.reader import open_bundle
from ..manifest.schema import (
    load_manifest_file,
    validate_manifest,
    validate_manifest_against_probe,
)
from ..probe import probe_video_file
from ..render import plan_render, render_plan_to_file
from ..security.errors import CompositionPlanError, ManifestValidationError
from .planner import plan_composition



def compose_bundles_to_file(
        bundle_paths, core_input, output_path, canvas_width, canvas_height,
        layout_mode="horizontal", audio_mode="core", audio_file=None,
        entry_fade_seconds=0.0, background_color=None, fps=None,
        codec="libx264", audio_codec="aac"):
    if not isinstance(bundle_paths, list) or len(bundle_paths) < 2:
        raise CompositionPlanError("compose requires at least two bundle paths")

    with ExitStack() as stack:
        clips = []
        for index, bundle_path in enumerate(bundle_paths):
            opened_bundle = stack.enter_context(open_bundle(bundle_path))
            manifest_raw = load_manifest_file(opened_bundle["manifest_path"])
            manifest = validate_manifest(manifest_raw)

            if manifest["video_file"] != opened_bundle["video_name"]:
                raise ManifestValidationError(
                    "video_file does not match the video file in the bundle",
                    field="video_file",
                    declared_video_file=manifest["video_file"],
                    actual_video_file=opened_bundle["video_name"],
                )

            probe_info = probe_video_file(opened_bundle["video_path"])
            validate_manifest_against_probe(manifest, probe_info)
            clips.append(
                {
                    "bundle_id": f"clip_{index}",
                    "source_path": opened_bundle["video_path"],
                    "manifest": manifest,
                    "probe": probe_info,
                }
            )

        composition_plan = plan_composition(
            clips,
            core_input=core_input,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            layout_mode=layout_mode,
            entry_fade_seconds=entry_fade_seconds,
        )
        render_plan = plan_render(
            composition_plan,
            audio_mode=audio_mode,
            audio_file=audio_file,
            background_color=background_color,
        )
        render_result = render_plan_to_file(
            render_plan,
            output_path,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
        )

    return {
        "composition_plan": composition_plan,
        "render_plan": render_plan,
        "render_result": render_result,
    }
