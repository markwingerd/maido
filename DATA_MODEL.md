# Maido Data Model

## 1. Canonical Artifacts

### 1.1 Bundle
A bundle is a portable artifact containing:
- one video file
- one manifest file

Recommended extension:
- `.maido.zip`

### 1.2 Manifest
A JSON document describing one source video's metadata.

Recommended filename:
- `maido.json`

### 1.3 Composition Request
A runtime object created by the CLI or library from:
- multiple bundles
- one designated core input
- output/render options

### 1.4 Composition Plan
An internal normalized plan created after validation and video probing.

This is not user-authored.

---

## 2. Bundle Layout

Recommended bundle structure:

```text
example.maido.zip
├── maido.json
└── source.mp4
```

### Constraints
- exactly one manifest file
- exactly one video file
- no symlinks
- no executable content
- no hidden extra files in v1

### Allowed video extensions for v1
Recommended:
- `.mp4`
- `.mov`
- `.mkv`
- `.webm`

The supported set should match what the installed MoviePy/ffmpeg stack can reliably process.

---

## 3. Manifest Model

The manifest describes per-video metadata only.

Whether a clip is the `core` video is **not** stored in the manifest.  
Core status is chosen at composition time.

Reason:
- the same bundle may be core in one composition and supporting in another
- role belongs to the composition request, not the bundle data contract

---

## 4. Manifest Fields

## 4.1 Required top-level fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `version` | string | yes | Manifest version, e.g. `"1"` |
| `video_file` | string | yes | Name of the video inside the bundle |
| `sync_point_seconds` | number | yes | Mandatory alignment point |
| `label` | string | no | Human-friendly name |

## 4.2 Optional top-level fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `center` | object | no | Crop center hint |
| `min_dimensions` | object | no | Minimum visible source dimensions |
| `preferred_direction` | string | no | `left`, `right`, `up`, or `down` |
| `notes` | string | no | Freeform user note |
| `tags` | array | no | Optional organizational labels |

---

## 5. Nested Object Definitions

## 5.1 `center`

Represents the important point around which crop planning should be biased.

Example:

```json
{
  "x": 200,
  "y": 300
}
```

Rules:
- both `x` and `y` are required if `center` is present
- both must be numeric
- values are interpreted in source pixel coordinates
- values must be within source bounds after video probe validation

---

## 5.2 `min_dimensions`

Represents the minimum source-space content that should remain visible after cropping.

Example:

```json
{
  "width": null,
  "height": 200
}
```

Rules:
- object is optional
- if present, at least one of `width` or `height` must be present and non-null
- provided values must be positive numbers
- `null` is allowed for one side if the other side is provided

Interpretation:
- these are source-space visibility constraints
- they are not output resolution targets

---

## 5.3 `preferred_direction`

Hard placement preference in the composed layout.

Allowed values:
- `left`
- `right`
- `up`
- `down`

Rules:
- optional
- if present, must be one of the enum values above
- conflicting direction requests should produce an explicit layout conflict error

---

## 6. Example Manifest

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

---

## 7. Manifest Validation Rules

## 7.1 Required rules
- `version` must exist
- `video_file` must exist
- `sync_point_seconds` must exist
- `sync_point_seconds >= 0`

## 7.2 Structural rules
- `center` requires both `x` and `y`
- `min_dimensions` requires at least one of `width` or `height`
- `preferred_direction` must be one of `left`, `right`, `up`, `down`

## 7.3 Referential rules
- `video_file` must match a real file inside the bundle
- v1 allows exactly one manifest and one video per bundle

## 7.4 Probe-backed rules
After video inspection:
- `sync_point_seconds <= source_duration`
- `center.x` must be within source width
- `center.y` must be within source height
- `min_dimensions.width <= source_width` if provided
- `min_dimensions.height <= source_height` if provided

## 7.5 Conflict rules
Validation should fail on conditions such as:
- impossible crop constraints
- incompatible directional demands
- unsupported file types
- malformed or unsafe archive contents

---

## 8. Composition Request Model

This object is created by the CLI or library when composing multiple bundles.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `inputs` | array | yes | Bundle paths or loaded bundle objects |
| `core_input` | string or integer | yes | Identifies which input is the core clip |
| `output_file` | string | yes | Output path |
| `layout_mode` | string | no | `auto`, `horizontal`, `grid` |
| `audio_mode` | string | no | `core`, `mute`, `file` |
| `audio_file` | string | no | Required when `audio_mode=file` |
| `debug` | boolean | no | Render overlays if true |
| `entry_fade_seconds` | number | no | Optional fade-in for delayed supporting clips |

### Default recommendations
- `layout_mode = auto`
- `audio_mode = core`
- `debug = false`
- `entry_fade_seconds = 0` or a small fixed value such as `0.15`

---

## 9. Core-Referenced Timeline Semantics

The composition timeline is anchored to the core video.

Rules:
- output time `0` corresponds to core video time `0`
- output end corresponds to core video end by default
- the core sync point defines the reference sync moment
- each supporting clip is shifted so its sync point lands at the same output time as the core sync point
- if a supporting clip begins after output time `0`, its cell remains black until it appears
- if alignment requires pre-sync footage that does not exist, the supporting clip is trimmed at the start
- if a supporting clip ends before the core ends, its cell is black for the remainder

---

## 10. Audio Model

Audio is composition-level policy.

Supported v1 policies:
- `core`
  - preserve only the core video's audio
- `mute`
  - output no audio
- `file`
  - replace output audio with an explicit external file

Supporting clip audio is ignored in v1.

---

## 11. Composition Plan Model

This is an internal normalized object computed after validation and probing.

Suggested fields:

| Field | Meaning |
|---|---|
| `bundle_id` | Stable internal identifier |
| `role` | `core` or `supporting` |
| `source_path` | Safe resolved path or handle |
| `source_width` | Probed width |
| `source_height` | Probed height |
| `source_duration` | Probed duration |
| `sync_point_seconds` | Normalized sync point |
| `output_start_seconds` | Clip start on output timeline |
| `output_end_seconds` | Clip end on output timeline |
| `trim_start_seconds` | Source trim-in point |
| `trim_end_seconds` | Source trim-out point |
| `crop_x` | Planned source crop x |
| `crop_y` | Planned source crop y |
| `crop_width` | Planned source crop width |
| `crop_height` | Planned source crop height |
| `cell_x` | Output cell x |
| `cell_y` | Output cell y |
| `cell_width` | Output cell width |
| `cell_height` | Output cell height |
| `placement_direction` | Resolved placement |
| `debug_annotations` | Overlay instruction data |

This is an internal data structure only.

---

## 12. Error Model

Even if implementation stays simple, errors should be categorized clearly.

Recommended categories:
- `archive_error`
- `manifest_parse_error`
- `manifest_validation_error`
- `video_probe_error`
- `layout_conflict_error`
- `crop_conflict_error`
- `render_error`

Each error should include, where possible:
- category
- short message
- bundle/file reference
- field name
- actionable hint

Example:
- category: `manifest_validation_error`
- message: `min_dimensions requires width or height`
- field: `min_dimensions`

---

## 13. Debug Overlay Model

Debug rendering should be driven by structured overlay data rather than ad hoc drawing logic.

Recommended overlay elements:
- center crosshair
- min-dimensions rectangle
- selected crop rectangle
- sync marker
- placement badge
- label text
- time-to-sync or sync-reached indicator

This makes debug behavior testable and easier to evolve.

---

## 14. Versioning Strategy

Manifest versioning should be explicit.

Recommended field:
- `"version": "1"`

Rules:
- reject unknown major versions
- allow additive optional fields within a major version
- preserve backward compatibility where practical

---

## 15. Recommendation Summary

Canonical v1 data model:
- bundle: `.maido.zip`
- manifest: `maido.json`
- required manifest fields:
  - `version`
  - `video_file`
  - `sync_point_seconds`
- optional manifest fields:
  - `label`
  - `center`
  - `min_dimensions`
  - `preferred_direction`
- composition-level fields:
  - `core_input`
  - `audio_mode`
  - `audio_file`
  - `layout_mode`
- validation style:
  - plain Python
  - explicit checks
  - no Pydantic
  - no typing-heavy design
