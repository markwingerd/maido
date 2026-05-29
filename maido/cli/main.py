import argparse
import json

from maido.bundle.inspection import inspect_bundle_path
from maido.security.errors import MaidoError


def build_parser():
    parser = argparse.ArgumentParser(prog="maido")
    subparsers = parser.add_subparsers(dest="command")

    bundle_parser = subparsers.add_parser("bundle", help="bundle-related commands")
    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_command")

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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bundle" and args.bundle_command == "inspect":
        return _run_bundle_inspect(args)

    parser.print_help()
    return 1


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

    if manifest.get("preferred_direction"):
        lines.append(f"Preferred direction: {manifest['preferred_direction']}")

    for warning in manifest.get("warnings", []):
        lines.append(f"Warning: {warning}")

    return "\n".join(lines)
