# Vision Pipeline

## Pipeline Stages

```
FrameData → ImageProcessor → ProcessedFrame → PartDetector → DetectionResult
```

Orchestrated by `VisionApplication.process_one_frame()` in `app.py`.

## Processing Modes

Configured via `vision.processing_mode`:

| Mode | Behaviour |
|---|---|
| `live` | continuous loop while the application runs; publishes to the web dashboard |
| `single_frame` | one pipeline pass, log summary, exit (useful for scripted checks) |
| `debug` | live loop + local OpenCV window with overlay (Q/ESC quits) |

## Pre-processing (`processing/image_processor.py`)

Milestone 1 is pass-through. Planned M3/M4 additions (each appended to
`ProcessedFrame.operations` for traceability): grayscale/HSV conversion,
blur/denoise, illumination normalization.

## Detection (`detection/`)

- Contract: `PartDetector.configure(ReferenceSet, threshold, params)` then
  `detect(ProcessedFrame) → DetectionResult`.
- Current implementation: `OpenCVDetector` — per frame:
  1. grayscale → Gaussian blur → Otsu (or fixed) threshold → morphological
     open/close → binary mask (`invert: true` for dark parts on light bg)
  2. external contours; reject below `min_area_px` or outside the
     area-fraction bounds derived from the reference images (× `area_tolerance`)
  3. `cv2.matchShapes` (Hu moments, scale/rotation invariant) against every
     reference contour; confidence = 1/(1 + `match_scale`·distance)
  4. accepted contours → `Detection` with centroid (moments), bounding box,
     and metadata (area_px, shape_distance)
- References are processed once in `configure()`: largest **fully-visible**
  contour per image (border-touching blobs are treated as background clutter)
  that fills at least `min_reference_area_fraction` of the image; unusable
  images are skipped with an actionable warning, and configuration fails only
  if no reference is usable.
- Planned alternative: `YOLODetector` implementing the same contract.
- Validation tool: `python scripts/detect_check.py [images...|--live]` writes
  annotated results to `logs/detect_check/`.

## Reference Datasets

- `parts/<part_name>/` holds reference images (`.jpg/.jpeg/.png/.bmp`).
- `load_reference_set()` validates the folder at startup and raises
  `ReferenceDataError` with the list of available parts if misconfigured.
- Changing `vision.active_part` (or replacing folder contents and restarting)
  switches the detection target with zero code changes.

## Part Counting

`DetectionResult.detection_count` is a property over `detections[]` — the
count can never disagree with the detection list. Zero detections is a valid,
non-error result that flows through the whole pipeline.

Count reliability is validated with
`python scripts/detect_check.py --live --frames 30`, which reports per-frame
counts and the stability percentage of the dominant count (M5 acceptance:
100% over 30 frames with 3 parts).

## Output Contract

See DATA_FLOW.md for the full `DetectionResult` / `Detection` structure and
COORDINATE_SYSTEM.md for the pixel coordinate convention.

## Live Visualization

After each frame, `VisionApplication._publish()` draws the overlay
(`visualization/overlay.py`), JPEG-encodes it, and stores it with a status
snapshot in `web.LiveState`. The dashboard at `http://<host>:8000/` shows the
MJPEG stream (`/stream`) and polls `/api/status` (count, detections px,
targets mm, robot state, fps). Overlay/encoding is skipped entirely when the
web UI is disabled and the mode is not `debug`.
