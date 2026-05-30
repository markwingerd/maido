import unittest

from maido.composition import plan_composition
from maido.render import plan_render, render_plan_to_file
from maido.security.errors import RenderExecutionError


def _require_last_write(fake_api):
    if fake_api.last_write is None:
        raise AssertionError("expected a render write record")
    return fake_api.last_write


class RenderExecutorTests(unittest.TestCase):
    def test_render_plan_to_file_executes_core_audio_render(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "source_path": "core.mp4",
                    "manifest": {"sync_point_seconds": 4.0},
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
                {
                    "bundle_id": "support",
                    "source_path": "support.mp4",
                    "manifest": {
                        "sync_point_seconds": 2.0,
                        "preferred_direction": "right",
                    },
                    "probe": {
                        "width": 1280,
                        "height": 720,
                        "duration_seconds": 8.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
            layout_mode="horizontal",
            entry_fade_seconds=0.2,
        )
        render_plan = plan_render(composition_plan)
        fake_api = FakeMoviePyApi()

        result = render_plan_to_file(
            render_plan,
            "output.mp4",
            moviepy_api=fake_api,
        )

        self.assertEqual(result["output_path"], "output.mp4")
        self.assertEqual(result["fps"], 30.0)
        last_write = _require_last_write(fake_api)
        self.assertEqual(last_write["output_path"], "output.mp4")
        self.assertEqual(last_write["fps"], 30.0)
        self.assertEqual(last_write["codec"], "libx264")
        self.assertEqual(last_write["audio_codec"], "aac")
        self.assertEqual(last_write["clip_count"], 3)
        self.assertEqual(fake_api.composite_audio_file, None)

    def test_render_plan_to_file_supports_external_audio(self):
        composition_plan = plan_composition(
            [
                {
                    "bundle_id": "core",
                    "source_path": "core.mp4",
                    "manifest": {"sync_point_seconds": 4.0},
                    "probe": {
                        "width": 1920,
                        "height": 1080,
                        "duration_seconds": 10.0,
                    },
                },
            ],
            core_input=0,
            canvas_width=1920,
            canvas_height=1080,
        )
        render_plan = plan_render(
            composition_plan,
            audio_mode="file",
            audio_file="music.mp3",
            background_color="#000000",
        )
        fake_api = FakeMoviePyApi(audio_duration=30.0)

        render_plan_to_file(render_plan, "output.mp4", fps=24.0, moviepy_api=fake_api)

        last_write = _require_last_write(fake_api)
        self.assertEqual(last_write["fps"], 24.0)
        self.assertEqual(fake_api.composite_audio_file, "music.mp3")
        self.assertEqual(fake_api.background_color, (0, 0, 0))

    def test_render_plan_to_file_rejects_missing_fields(self):
        with self.assertRaises(RenderExecutionError):
            render_plan_to_file({"clips": []}, "output.mp4", moviepy_api=FakeMoviePyApi())


class FakeMoviePyApi:
    def __init__(self, audio_duration=5.0):
        self.vfx = FakeVfx()
        self.background_color = None
        self.last_write = None
        self.composite_audio_file = None
        self._audio_duration = audio_duration

    def ColorClip(self, size, color):
        self.background_color = color
        return FakeClip(self, "background", duration=None)

    def VideoFileClip(self, source_path):
        return FakeClip(self, source_path, duration=10.0)

    def CompositeVideoClip(self, clips, size):
        return FakeCompositeClip(self, clips, size)

    def AudioFileClip(self, source_path):
        return FakeAudioClip(self, source_path, duration=self._audio_duration)


class FakeVfx:
    def fadein(self, clip, duration):
        return clip


class FakeClip:
    def __init__(self, api, source_path, duration):
        self.api = api
        self.source_path = source_path
        self.duration = duration
        self.audio_removed = False

    def set_duration(self, duration):
        self.duration = duration
        return self

    def subclip(self, start, end):
        self.subclip_range = (start, end)
        return self

    def crop(self, x1, y1, x2, y2):
        self.crop_box = (x1, y1, x2, y2)
        return self

    def resize(self, newsize):
        self.newsize = newsize
        return self

    def fx(self, effect, duration):
        self.fade_duration = duration
        return effect(self, duration)

    def set_start(self, start):
        self.start = start
        return self

    def set_position(self, position):
        self.position = position
        return self

    def without_audio(self):
        self.audio_removed = True
        return self

    def set_audio(self, audio):
        self.audio = audio
        return self

    def close(self):
        self.closed = True


class FakeAudioClip(FakeClip):
    pass


class FakeCompositeClip(FakeClip):
    def __init__(self, api, clips, size):
        super().__init__(api, "composite", duration=None)
        self._clips = clips
        self.size = size

    def set_audio(self, audio):
        self.api.composite_audio_file = audio.source_path
        self.audio = audio
        return self

    def write_videofile(self, output_path, fps, codec, audio_codec):
        self.api.last_write = {
            "output_path": output_path,
            "fps": fps,
            "codec": codec,
            "audio_codec": audio_codec,
            "clip_count": len(self._clips),
        }


if __name__ == "__main__":
    unittest.main()
