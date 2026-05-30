# Maido Agent Guide

## 1. Role

You are working on `maido` as a senior software architect and implementation planner.

Your job is to:
- preserve modular architecture
- prioritize safe input handling
- keep the implementation small and understandable
- avoid premature complexity
- respect the project preference against `typing`-heavy and `pydantic`-based design

---

## 2. Hard Guardrails

### Do
- keep work aligned with `ARCHITECTURE.md`
- keep data contracts aligned with `DATA_MODEL.md`
- favor plain Python data handling and explicit validation
- treat all zip bundles and video files as untrusted input
- fail fast on invalid or conflicting metadata
- keep modules small and responsibility-focused

### Do not
- do not introduce Pydantic unless a third-party dependency absolutely requires it
- do not build the design around extensive Python type annotations
- do not use unsafe YAML parsing
- do not extract zip archives without path validation
- do not execute anything from user-provided bundles
- do not shell-interpolate user input into ffmpeg or related commands
- do not silently resolve layout conflicts that should be explicit errors

---

## 3. Product Intent

The product is:
- a Python library
- a CLI
- later, possibly a worker component for a web API

The product is not:
- a full video editor
- a GUI-first application
- an auto-sync computer vision system in v1

---

## 4. Core Video Rule

Every multi-video composition must have exactly one core video.

Implementation must assume:
- the core video defines the authoritative output timeline
- the core video defines the reference sync moment
- the core video is the only source of preserved audio by default
- non-core videos must adapt to the core timeline, not the reverse

Do not design the planner as if all clips have equal authority.

---

## 5. Implementation Priorities

Priority order:

1. Safe bundle ingestion
2. Clear manifest validation
3. Correct core-referenced sync alignment
4. Predictable crop planning
5. Stable layout selection
6. Composition rendering
7. Debug render support
8. CLI ergonomics
9. Future web-service hardening

If forced to choose, correctness and safety beat convenience.

---

## 6. Required Architectural Boundaries

Implementation should be split into modules with clear responsibilities:

- `bundle`
  - read, validate, and package archives
- `manifest`
  - parse and validate JSON manifests
- `probe`
  - inspect video metadata
- `sync`
  - align timeline around the core sync point
- `layout`
  - assign output cells and directional placement
- `crop`
  - compute source crop windows
- `render`
  - execute MoviePy composition
- `debug`
  - generate overlay previews
- `cli`
  - user-facing command interface
- `security`
  - shared safety checks and limits

Avoid merging these concerns into one large script.

---

## 7. Security Rules

### Archive handling
- reject absolute paths
- reject `..` path traversal
- reject symlinks
- reject unexpected extra files
- enforce archive size limits
- extract only to isolated temp directories

### Manifest handling
- canonical format is JSON
- use standard safe JSON parsing
- validate every field explicitly
- never treat manifest values as executable content

### Video handling
- treat decoders as a high-risk boundary
- probe before full render
- enforce max duration, max dimensions, and max fps where possible
- run in low-privilege contexts when used as a service

### Shell/process safety
- avoid shell string building from user input
- prefer direct argument passing
- sanitize temp paths
- clean temp artifacts aggressively

---

## 8. Timeline Behavior Requirements

For supporting clips:
- delayed starts must render as black until the clip begins
- optional quick fade-in may be applied when a delayed clip appears
- clips that cannot provide enough pre-sync footage must be trimmed at the start
- clips that end before the core ends should leave black in their reserved region

These behaviors should be deterministic and easy to explain to users.

---

## 9. Audio Rules

Audio is composition-level policy.

For v1:
- preserve only the core audio by default
- allow mute mode
- allow explicit external replacement audio if requested

Do not mix multiple source audio tracks in v1 unless explicitly re-scoped later.

---

## 10. UX Rules

### CLI should be clear, not clever
The CLI should guide users through a straightforward workflow:

1. create or pack a bundle
2. inspect/debug a bundle
3. compose multiple bundles around a chosen core video

### Layout rules for v1
- v1 supports only `horizontal` and `vertical` composition layouts
- `horizontal` is the default layout mode
- the core clip must be placed at index `(n - 1) // 2`
- cross-axis preference contradictions must be explicit errors
- same-side preference collisions should not error; resolve them deterministically using CLI order and remaining slot availability

### Validation errors must be actionable
Bad:
- `Invalid input`

Good:
- `preferred_direction must be one of left, right, up, down`
- `sync_point_seconds (12.4) exceeds source duration (10.8 seconds)`
- `multiple clips requested left placement but the layout only has one left-most slot`

### Debug mode must visualize assumptions
A debug preview should make it obvious:
- where the sync point is
- where the crop center is
- what minimum dimensions are being protected
- what crop was selected
- where the clip was placed in the final layout
- when a clip becomes visible relative to the core timeline

---

## 11. Recommended Delivery Phases

## Phase 1: Data contract and packaging
Deliver:
- manifest format
- bundle reader
- safe archive validation
- CLI for bundle init/pack/inspect

## Phase 2: Planning engine
Deliver:
- video probe
- core-referenced sync planner
- layout planner
- crop planner

## Phase 3: Rendering
Deliver:
- composition renderer
- output writing
- core/mute/file audio policy

## Phase 4: Debugging support
Deliver:
- single-bundle debug preview
- composition debug overlays

## Phase 5: Hardening
Deliver:
- better error surfaces
- resource limits
- service-readiness notes
- regression tests for malformed bundles

---

## 12. Testing Priorities

Test behavior, not framework ceremony.

### Archive tests
- valid bundle
- missing manifest
- missing video
- multiple videos
- path traversal attempt
- zip bomb policy behavior

### Manifest tests
- missing sync point
- invalid enum values
- partial `center`
- empty `min_dimensions`
- sync point beyond duration

### Planner tests
- 2-video alignment against a core
- 3+ video grid placement
- conflicting direction claims
- impossible crop constraints
- supporting clip delayed after output start
- supporting clip trimmed at start to match core
- supporting clip ending before core end

### Debug tests
- overlays appear where expected
- sync marker appears at expected time
- crop rectangle reflects planner output

### Render tests
- basic successful render
- duration matches core duration
- only core audio preserved in default mode
- mute mode produces no audio
- output resolution checks

---

## 13. Decision Rules for Ambiguity

When implementation details are unclear, follow these rules:

1. prefer explicit user control over hidden magic
2. prefer deterministic behavior over heuristic behavior
3. prefer a validation error over a silent wrong guess
4. prefer a simpler stable v1 over an ambitious fragile v1
5. prefer JSON + CLI helpers over YAML complexity
6. prefer isolated worker execution for untrusted media
7. prefer core-referenced behavior over symmetric clip negotiation

---

## 14. Coding Preference Constraints

Unless forced by a third-party requirement:
- do not introduce Pydantic
- do not make the design depend on rich Python typing features
- do not create unnecessary abstractions only to model types
- use plain objects, dictionaries, and explicit validation paths

This project should remain understandable to developers who prefer straightforward Python.

---

## 15. Definition of Done for v1

`maido` v1 is “done enough” when it can:

- package one video + manifest into a bundle
- validate bundle contents safely
- read multiple bundles
- require one explicit core video for composition
- align supporting videos to the core sync point
- auto-crop around optional center hints
- respect optional min-dimension constraints
- honor optional preferred direction when feasible
- render a final multi-video composition
- preserve only core audio by default
- optionally mute or replace audio
- render a debug preview showing metadata assumptions
- provide clear errors for invalid or conflicting input

If all of the above work reliably, the architecture has succeeded.
