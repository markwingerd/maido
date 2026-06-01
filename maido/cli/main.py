import argparse
import json
import os

from ..bundle.inspection import inspect_bundle_path
from ..bundle.packing import pack_bundle
from ..composition import compose_bundles_to_file
from ..manifest.template import build_manifest_data, write_manifest_file
from ..security.errors import MaidoError


def build_parser():
    parser = argparse.ArgumentParser(prog="maido")
    subparsers = parser.add_subparsers(dest="command")

    bundle_parser = subparsers.add_parser("bundle", help="bundle-related commands")
    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_command")

    init_parser = bundle_subparsers.add_parser(
        "init",
        help="create a starter maido manifest for a video file",
    )
    init_parser.add_argument("video_path", help="path to the source video file")
    init_parser.add_argument(
        "--sync-point",
        required=True,
        type=float,
        help="required sync point in seconds",
    )
    init_parser.add_argument("--label", help="optional human-readable label")
    init_parser.add_argument("--center-x", type=float, help="optional crop center x")
    init_parser.add_argument("--center-y", type=float, help="optional crop center y")
    init_parser.add_argument("--min-width", type=float, help="optional minimum width")
    init_parser.add_argument("--min-height", type=float, help="optional minimum height")
    init_parser.add_argument("--max-width", type=float, help="optional maximum width")
    init_parser.add_argument("--max-height", type=float, help="optional maximum height")
    init_parser.add_argument(
        "--preferred-direction",
        choices=["left", "right", "up", "down"],
        help="optional hard placement preference",
    )
    init_parser.add_argument("--notes", help="optional notes field")
    init_parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="optional tag; can be provided multiple times",
    )
    init_parser.add_argument(
        "--output",
        help="path to write the manifest file; defaults to maido.json next to the video",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing manifest file",
    )

    pack_parser = bundle_subparsers.add_parser(
        "pack",
        help="validate and package a video plus manifest into a .maido.zip bundle",
    )
    pack_parser.add_argument("video_path", help="path to the source video file")
    pack_parser.add_argument("manifest_path", help="path to the manifest JSON file")
    pack_parser.add_argument(
        "--output",
        help="path to the output .maido.zip bundle",
    )
    pack_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output bundle",
    )

    inspect_parser = bundle_subparsers.add_parser(
        "inspect",
        help="safely validate and inspect a bundle",
    )
    inspect_parser.add_argument("bundle_path", help="path to the .maido.zip bundle")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="print the inspection result as JSON",
    )

    compose_parser = subparsers.add_parser(
        "compose",
        help="compose multiple bundles into a final output video",
    )
    compose_parser.add_argument(
        "bundle_paths",
        nargs="+",
        help="input bundle paths in CLI order",
    )
    compose_parser.add_argument(
        "--core",
        required=True,
        type=int,
        help="0-based index of the core bundle in the input list",
    )
    compose_parser.add_argument(
        "--output",
        required=True,
        help="path to the output video file",
    )
    compose_parser.add_argument(
        "--canvas-width",
        required=True,
        type=float,
        help="output canvas width in pixels",
    )
    compose_parser.add_argument(
        "--canvas-height",
        required=True,
        type=float,
        help="output canvas height in pixels",
    )
    compose_parser.add_argument(
        "--layout",
        choices=["horizontal", "vertical"],
        default="horizontal",
        help="composition layout mode",
    )
    compose_parser.add_argument(
        "--audio",
        choices=["core", "mute", "file"],
        default="core",
        help="output audio mode",
    )
    compose_parser.add_argument(
        "--audio-file",
        help="external audio file used when --audio file is selected",
    )
    compose_parser.add_argument(
        "--entry-fade-seconds",
        type=float,
        default=0.0,
        help="fade-in duration for delayed supporting clips",
    )
    compose_parser.add_argument(
        "--background-color",
        help="background color name or #RRGGBB value",
    )
    compose_parser.add_argument(
        "--fps",
        type=float,
        help="output frames per second",
    )
    compose_parser.add_argument(
        "--codec",
        default="libx264",
        help="video codec passed to MoviePy",
    )
    compose_parser.add_argument(
        "--audio-codec",
        default="aac",
        help="audio codec passed to MoviePy",
    )
    compose_parser.add_argument(
        "--overwrite-size",
        action="store_true",
        help="allow the planner to preserve the core minimum size even when the canvas is too small",
    )

    return parser



def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bundle" and args.bundle_command == "init":
        return _run_bundle_init(args)
    if args.command == "bundle" and args.bundle_command == "pack":
        return _run_bundle_pack(args)
    if args.command == "bundle" and args.bundle_command == "inspect":
        return _run_bundle_inspect(args)
    if args.command == "compose":
        return _run_compose(args)

    parser.print_help()
    return 1



def _run_bundle_init(args):
    try:
        if not os.path.isfile(args.video_path):
            raise MaidoError("video file does not exist", path=args.video_path)

        center = _build_center_argument(args.center_x, args.center_y)
        min_dimensions = _build_dimensions_argument(args.min_width, args.min_height)
        max_dimensions = _build_dimensions_argument(args.max_width, args.max_height)
        output_path = args.output or os.path.join(
            os.path.dirname(os.path.abspath(args.video_path)),
            "maido.json",
        )

        if os.path.exists(output_path) and not args.force:
            raise MaidoError(
                "manifest file already exists; pass --force to overwrite it",
                path=output_path,
            )

        manifest = build_manifest_data(
            video_file=args.video_path,
            sync_point_seconds=args.sync_point,
            label=args.label,
            center=center,
            min_dimensions=min_dimensions,
            max_dimensions=max_dimensions,
            preferred_direction=args.preferred_direction,
            notes=args.notes,
            tags=args.tags,
        )
        write_manifest_file(output_path, manifest)
    except MaidoError as error:
        print(json.dumps(error.to_dict(), indent=2))
        return 2

    print(f"Wrote manifest: {output_path}")
    return 0



def _run_bundle_pack(args):
    try:
        result = pack_bundle(
            args.video_path,
            args.manifest_path,
            output_path=args.output,
            overwrite=args.force,
        )
    except MaidoError as error:
        print(json.dumps(error.to_dict(), indent=2))
        return 2

    print(f"Created bundle: {result['bundle_path']}")
    return 0



def _run_bundle_inspect(args):
    try:
        report = inspect_bundle_path(args.bundle_path)
    except MaidoError as error:
        print(json.dumps(error.to_dict(), indent=2))
        return 2

    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_inspection_report(report))

    return 0



def _run_compose(args):
    try:
        result = compose_bundles_to_file(
            args.bundle_paths,
            core_input=args.core,
            output_path=args.output,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            layout_mode=args.layout,
            audio_mode=args.audio,
            audio_file=args.audio_file,
            entry_fade_seconds=args.entry_fade_seconds,
            background_color=args.background_color,
            fps=args.fps,
            codec=args.codec,
            audio_codec=args.audio_codec,
            allow_size_override=args.overwrite_size,
        )
    except MaidoError as error:
        print(json.dumps(error.to_dict(), indent=2))
        return 2

    render_result = result["render_result"]
    print(
        f"Created video: {render_result['output_path']} "
        f"({render_result['clip_count']} clips)"
    )
    return 0



def _build_center_argument(center_x, center_y):
    if center_x is None and center_y is None:
        return None
    if center_x is None or center_y is None:
        raise MaidoError("center requires both --center-x and --center-y")
    return {"x": center_x, "y": center_y}



def _build_dimensions_argument(width, height):
    if width is None and height is None:
        return None
    return {"width": width, "height": height}



def _format_inspection_report(report):
    manifest = report["manifest"]
    probe = report["probe"]
    archive = report["archive"]

    lines = [
        f"Bundle: {report['bundle_path']}",
        f"Manifest: {archive['manifest_name']}",
        f"Video: {archive['video_name']}",
        f"Duration: {probe['duration_seconds']:.3f} seconds",
        f"Resolution: {probe['width']}x{probe['height']}",
        f"FPS: {probe['fps'] if probe['fps'] is not None else 'unknown'}",
        f"Sync point: {manifest['sync_point_seconds']:.3f} seconds",
    ]

    if manifest.get("label"):
        lines.append(f"Label: {manifest['label']}")

    if manifest.get("center"):
        lines.append(
            f"Center: ({manifest['center']['x']:.3f}, {manifest['center']['y']:.3f})"
        )

    if manifest.get("min_dimensions"):
        min_dimensions = manifest["min_dimensions"]
        lines.append(
            "Minimum dimensions: "
            f"width={min_dimensions.get('width')}, height={min_dimensions.get('height')}"
        )

    if manifest.get("max_dimensions"):
        max_dimensions = manifest["max_dimensions"]
        lines.append(
            "Maximum dimensions: "
            f"width={max_dimensions.get('width')}, height={max_dimensions.get('height')}"
        )

    if manifest.get("preferred_direction"):
        lines.append(f"Preferred direction: {manifest['preferred_direction']}")

    for warning in manifest.get("warnings", []):
        lines.append(f"Warning: {warning}")

    return "\n".join(lines)
