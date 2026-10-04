# Coordinate Systems

Two coordinate systems exist and are never mixed implicitly.

## Image Coordinates (pixels)

```
(0,0) ──────► X (positive right)
  │
  │      e.g. center_x_px, center_y_px in Detection
  ▼
  Y (positive down)
```

- Origin: **top-left** of the image
- Unit: pixels (float for sub-pixel centers)
- Used in: `FrameData`, `Detection`, `BoundingBox`

## Robot Coordinates (millimetres)

- Defined by the Delta robot controller's frame (exact convention to be
  confirmed against the controller in Milestone 7/8)
- Unit: millimetres
- Used in: `RobotCoordinate`, `PickTarget`, `WorkspaceBounds`
- Z is **constant per pick** and comes from `robot.pick_z` config, because the
  camera is mounted perpendicular above a flat workspace

## Transformation

```
(x_px, y_px)  ──►  CoordinateTransformer.image_to_robot()  ──►  RobotCoordinate(x_mm, y_mm, pick_z)
```

| Implementation | Method | Status |
|---|---|---|
| `IdentityTransformer` | passthrough (px treated as mm) — development only | fallback when no calibration file |
| `HomographyTransformer` | 3×3 planar homography, constant Z | auto-loaded from `calibration/homography.yaml` |

## Calibration Procedure (Milestone 7)

Setup assumption (confirmed): fixed camera, perpendicular to a flat workspace,
constant pick height → planar homography is sufficient.

1. Mount the camera in its final position (any camera/workspace movement
   invalidates the calibration).
2. Place ≥4 markers in the camera view (spread them wide, not collinear;
   more points → least-squares fit → better accuracy). Measure/jog the robot
   to each marker and note its robot X/Y (mm).
3. Run `python scripts/calibrate.py` — click each marker in the live window
   (U undo, ENTER done), then type its robot X/Y in the console.
   Headless alternative: `--from-file points.yaml` with
   `points: [{pixel: [x, y], robot: [x, y]}, ...]`.
4. The tool fits the homography (`cv2.findHomography`), reports RMS and max
   reprojection error in mm (warns above 2 mm RMS), and saves to
   `calibration/homography.yaml` (path from `system.calibration_file`):
   created timestamp, errors, point pairs, 3×3 matrix.
5. Check with `python scripts/calibrate.py --verify` (reprojects stored points).

At startup `load_transformer()` uses the saved calibration
(`HomographyTransformer`); if none exists it falls back to
`IdentityTransformer` with a warning (robot coords = raw pixels — development
only, never pick with it).

Re-calibration is required whenever the camera or workspace moves.

## Safety

`PickTargetManager` rejects any transformed coordinate outside
`robot.workspace` bounds before it can reach the robot (WARNING logged).
