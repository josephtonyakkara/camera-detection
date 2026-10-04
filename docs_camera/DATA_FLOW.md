# Data Flow

## End-to-End Pipeline

```
Camera hardware
  │  raw image (BGR ndarray)
  ▼
CameraManager.get_frame()
  │  FrameData { frame_id, timestamp, image, width, height, color_format }
  ▼
ImageProcessor.process()
  │  ProcessedFrame { source: FrameData, image, operations[] }
  ▼
PartDetector.detect()
  │  DetectionResult { frame_id, timestamp, image_width/height,
  │                    detection_count, detections[] }
  │  each Detection { class_name, confidence, center_x_px, center_y_px,
  │                   bounding_box, metadata }
  ▼
PickTargetManager.generate_targets()
  │  list[PickTarget] { target_id, coordinate: RobotCoordinate(x,y,z mm),
  │                     class_name, confidence, source_frame_id, created_at }
  ▼
RobotInterface.send_pick_target()
  │  target published to robot controller (OPC UA nodes in M10)
  ▼
Delta robot
```

## Transition Details

| Producer → Consumer | Data | Transformation | Possible errors |
|---|---|---|---|
| Camera driver → CameraManager | `FrameData` | none (manager adds reconnect) | `CameraError` (open/read failure) |
| CameraManager → ImageProcessor | `FrameData` | pre-processing chain (pass-through in M1) | none currently |
| ImageProcessor → PartDetector | `ProcessedFrame` | matching against `ReferenceSet` | `DetectorError` (not configured) |
| PartDetector → PickTargetManager | `DetectionResult` | pixel→robot transform, Z from config, workspace filter, strategy ordering, cross-frame dedup (in-progress/cooldown locations suppressed) | `TransformError` (skipped per-detection) |
| PickTargetManager → RobotInterface | one `PickTarget` per `select_next()` | dispatched only when robot ready; one target in flight | `RobotError` (logged; slot released for retry) |
| RobotInterface → PickTargetManager | `RobotStatus.last_pick_target_id` | pick acknowledgement starts the location cooldown | stale ids ignored with warning |

## Important Semantics

- **Zero detections is not an error**: `DetectionResult` with `detection_count == 0` and
  `detections == []` flows through normally and produces an empty target list.
- **Out-of-workspace detections** are dropped by `PickTargetManager` with a WARNING log.
- **Robot not ready**: targets are not sent; a WARNING is logged. Nothing pretends success.
- **Camera read failure**: `CameraManager` closes and re-opens the driver once per call;
  persistent failure raises `CameraError` up to the application loop.

## Configuration Flow

```
config/*.yaml → load_config() → AppConfig → VisionApplication constructor
                                              ├── CameraConfig → CameraManager
                                              ├── VisionConfig → detector factory + reference loader
                                              ├── RobotConfig  → PickTargetManager + robot factory
                                              └── SystemConfig → logging, calibration path, web
```
