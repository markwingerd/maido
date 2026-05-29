# maido

`maido` is a Python library and CLI for combining multiple videos into a single synchronized split-screen video.

The main idea is simple:

- each input video has one important moment
- that moment is marked in metadata
- one video is chosen as the **core video**
- all other videos are aligned to the core
- the final output shows all videos playing at the same time

This is useful when you want to compare multiple recordings of the same event from different angles or devices.

---

## What maido does

`maido` is designed to:

- package a video together with its metadata
- validate that package safely
- align multiple videos using a required sync point
- automatically crop videos around an optional center point
- respect optional minimum visible dimensions
- place videos side by side or in a grid
- render a final combined video
- preserve only the core video's audio by default

---

## Core concept: the core video

Every composition must have exactly one **core video**.

The core video defines:

- the main output timeline
- the reference sync moment
- the default output duration
- the audio track that is preserved by default

All other videos are treated as supporting videos and must adapt to the core timeline.

That means:

- if a supporting clip starts too late relative to the core, its area begins as black and the clip appears later
- if a supporting clip would need footage before its own start to align with the core, it is trimmed at the beginning
- if a supporting clip ends before the core ends, its area becomes black for the rest of the output

---

## Bundle format

Each input video is expected to be packaged with its metadata in a zip bundle.

Recommended structure:

```text
example.maido.zip
├── maido.json
└── source.mp4
```

The metadata file is JSON.

JSON was chosen because it is:

- simple
- explicit
- easy to validate
- safer than YAML for untrusted input

---

## Manifest example

Example `maido.json`:

```json
{
  "version": "1",
  "video_file": "source.mp4",
  "label": "Camera A",
  "sync_point_seconds": 4.5,
  "center": {
    "x": 200,
    "y": 300
  },
  "min_dimensions": {
    "width": null,
    "height": 200
  },
  "preferred_direction": "left"
}
```

### Manifest fields

#### Required
- `version`
- `video_file`
- `sync_point_seconds`

#### Optional
- `label`
- `center`
- `min_dimensions`
- `preferred_direction`

### Notes
- `sync_point_seconds` is required for every video
- `center` helps choose the crop area
- `min_dimensions` protects important visible source area
- `preferred_direction` can request placement on `left`, `right`, `up`, or `down`

---

## Planned CLI workflows

`maido` is intended to support three main workflows.

### 1. Create or pack a bundle
Create metadata and package it with a video.

Planned commands:

```bash
maido bundle init
maido bundle pack
maido bundle inspect
```

### 2. Debug a bundle
Render a debug preview of a single bundle to visualize metadata assumptions.

Planned command:

```bash
maido debug input.maido.zip --output debug.mp4
```

The debug output should make it easy to see:

- where the sync point occurs
- where the crop center is
- what minimum dimensions are being protected
- what crop was selected

### 3. Compose multiple bundles
Create a final synchronized output from multiple bundles.

Planned command:

```bash
maido compose a.maido.zip b.maido.zip c.maido.zip --core 0 --output final.mp4
```

Planned options include:

- selecting the core input
- muting audio
- replacing audio with an external file
- enabling debug overlays

---

## Audio behavior

For v1, audio is intentionally simple.

Supported behavior:

- preserve only the **core video's** audio by default
- allow a mute mode
- allow an external replacement audio file

`maido` does **not** plan to mix audio from multiple source videos in v1.

---

## Security notes

`maido` is expected to handle zip bundles and video files that may come from untrusted sources.

Important security considerations:

- zip files must be validated before extraction
- path traversal such as `..` must be rejected
- absolute paths must be rejected
- symlinks inside archives must be rejected
- unexpected files should be rejected
- archive size limits should be enforced
- video files should be treated as unsafe input to media decoders
- processing should avoid shell interpolation of user input

JSON metadata does not execute code by itself, but all fields should still be validated explicitly.

---

## Project status

This project is currently in the planning and architecture stage.

The intended implementation priorities are:

1. safe bundle ingestion
2. manifest validation
3. core-referenced sync planning
4. crop and layout planning
5. rendering
6. debug preview support
7. CLI ergonomics
8. future web-service hardening

---

## Design constraints

This project intentionally prefers:

- plain Python
- explicit validation
- small focused modules
- understandable code

This project intentionally avoids:

- Pydantic
- heavy typing-driven architecture
- unsafe YAML parsing
- hidden magic when clear validation would be better

---

## Long-term intent

`maido` is being designed for:

- local CLI usage
- Python library usage
- possible future use inside a web API worker

The first version is focused on being reliable, explainable, and safe rather than overly ambitious.

---

## Summary

`maido` is a tool for:

- bundling videos with metadata
- aligning them around a required sync point
- treating one video as the core timeline
- automatically cropping and placing supporting videos
- rendering a final synchronized multi-video composition
```

If you want, I can also make this README a little more polished with sections like:

- `Installation`
- `Quick Start`
- `Project Layout`
- `Status / Roadmap`

while still keeping it simple.
