import contextlib
import io
import unittest
from unittest import mock

from maido.cli.main import main


class CliComposeCommandTests(unittest.TestCase):
    def test_compose_command_calls_workflow(self):
        stdout = io.StringIO()
        with mock.patch(
            "maido.cli.main.compose_bundles_to_file",
            return_value={
                "render_result": {
                    "output_path": "final.mp4",
                    "clip_count": 2,
                }
            },
        ) as compose_mock:
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "compose",
                        "left.maido.zip",
                        "core.maido.zip",
                        "--core",
                        "1",
                        "--output",
                        "final.mp4",
                        "--canvas-width",
                        "1920",
                        "--canvas-height",
                        "1080",
                        "--layout",
                        "horizontal",
                        "--audio",
                        "mute",
                        "--entry-fade-seconds",
                        "0.2",
                        "--overwrite-size",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(compose_mock.call_count, 1)
        self.assertIn("Created video: final.mp4", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
