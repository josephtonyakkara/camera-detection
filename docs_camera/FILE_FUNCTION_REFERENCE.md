# File and Function Reference

Complete overview of every Python file. Keep this in sync with code changes
(see AI_DEVELOPMENT_RULES.md).

## Module Dependency Chain

```
main.py
  └── app.py (VisionApplication)
        ├── config/loader.py ── config/models.py
        ├── camera/manager.py ── camera/base.py ── camera/usb_camera.py
        ├── processing/image_processor.py
        ├── detection/opencv_detector.py ── detection/base.py ── detection/reference_loader.py
        ├── coordinates/transformer.py
        ├── targets/pick_target_manager.py
        ├── robot/mock_robot.py ── robot/base.py
        ├── models/data.py            (used by all)
        └── utils/paths.py, utils/logging_setup.py
```

## models/data.py — shared data structures

All inter-module data. No logic beyond simple properties.

| Type | Kind | Key fields | Produced by | Consumed by |
|---|---|---|---|---|
| `ProcessingMode` | Enum | LIVE, SINGLE_FRAME, DEBUG | config | `app.py` |
| `RobotState` | Enum | DISCONNECTED…ERROR | robot impls | app, UI |
| `FrameData` | dataclass | frame_id, timestamp, image (ndarray), width, height, color_format | camera drivers | processor, detector |
| `ProcessedFrame` | dataclass | source (FrameData), image, operations[] | `ImageProcessor` | detectors |
| `BoundingBox` | frozen dataclass | x, y, width, height; `.center` property | detectors | UI, targets |
| `Detection` | dataclass | class_name, confidence, center_x_px/y_px, bounding_box, metadata | detectors | target manager |
| `DetectionResult` | dataclass | frame_id, timestamps, image size, detections[]; `.detection_count` property | detectors | target manager, UI |
| `RobotCoordinate` | frozen dataclass | x, y, z (mm) | transformer | target manager, robot |
| `PickTarget` | dataclass | target_id, coordinate, class_name, confidence, source_frame_id, created_at | target manager | robot interface |
| `RobotStatus` | dataclass | state, message, last_pick_target_id | robot impls | app, UI |

## config/models.py + config/loader.py

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| models.py | `CameraConfig` | camera.yaml as dataclass | — | — | — |
| models.py | `VisionConfig` | vision.yaml as dataclass | — | — | — |
| models.py | `WorkspaceBounds.contains()` | workspace limit check | x, y (mm) | bool | — |
| models.py | `RobotConfig` | robot.yaml as dataclass | — | — | — |
| models.py | `SystemConfig` | system.yaml as dataclass | — | — | — |
| models.py | `AppConfig` | aggregate of the four | — | — | — |
| loader.py | `load_config(config_dir)` | read 5 YAML files → AppConfig; missing files = defaults; unknown keys/invalid YAML raise `ConfigError` | config dir Path (default `config/`) | `AppConfig` | `_read_yaml`, `_build` |
| loader.py | `validate_config_data(name, data)` | validate one file's parsed mapping against its model (incl. nested workspace/opcua); used by the web config API | file stem, dict | — (raises `ConfigError`) | `_build` |
| loader.py | `CONFIG_FILES` | registry: file stem → (model, nested models) | — | — | — |

## camera/

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| base.py | `CameraInterface` (ABC) | contract for all drivers: `open(config)`, `get_frame()`, `is_open()`, `close()` | `CameraConfig` | `FrameData` | — |
| base.py | `CameraError` | camera failure exception | — | — | — |
| usb_camera.py | `USBCamera` | cv2.VideoCapture driver | `CameraConfig` | `FrameData` (BGR) | OpenCV |
| usb_camera.py | `enumerate_usb_cameras(max_index, with_snapshot)` | probe device indices, return responding cameras with resolution/snapshot | int, bool | `list[CameraProbe]` | OpenCV (DSHOW) |
| replay_camera.py | `ReplayCamera` | serves image files from `camera.replay_dir` in a loop (tests/dev without hardware) | `CameraConfig` | `FrameData` (BGR) | OpenCV imread |
| manager.py | `create_camera(type)` | driver factory | type string | `CameraInterface` | `USBCamera` (lazy import) |
| manager.py | `CameraManager.start()` | open with retry policy | — | — | `CameraInterface.open()` |
| manager.py | `CameraManager.get_frame()` | frame + one reconnect attempt on failure | — | `FrameData` | `CameraInterface.get_frame()` |
| manager.py | `CameraManager.stop()` | release device | — | — | `CameraInterface.close()` |

## processing/image_processor.py

| Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|
| `ImageProcessor.process()` | pre-processing chain (pass-through in M1; filters arrive in M3/M4) | `FrameData` | `ProcessedFrame` | — |

## detection/

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| base.py | `PartDetector` (ABC) | contract: `configure(references, threshold, params)`, `detect(frame)` | `ReferenceSet`, `ProcessedFrame` | `DetectionResult` | — |
| reference_loader.py | `ReferenceSet` | validated dataset: part_name, directory, image_paths, `.image_count` | — | — | — |
| reference_loader.py | `load_reference_set(parts_dir, part_name)` | validate `parts/<name>/`; raises `ReferenceDataError` if missing/empty | Paths | `ReferenceSet` | filesystem |
| opencv_detector.py | `OpenCVDetector.configure()` | read reference images, extract largest contour + area fraction each, derive area bounds; raises `DetectorError` if none usable | `ReferenceSet`, float, params dict | — | OpenCV |
| opencv_detector.py | `OpenCVDetector.detect()` | binarize → contours → area filter → Hu-moment shape match → detections with centroid/box/confidence | `ProcessedFrame` | `DetectionResult` | OpenCV |
| opencv_detector.py | `_binarize(image, params)` | grayscale+blur+threshold+morphology mask | ndarray, params | binary ndarray | OpenCV |

## coordinates/transformer.py

| Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|
| `CoordinateTransformer` (ABC) | contract: `image_to_robot(x_px, y_px)` | pixels | `RobotCoordinate` | — |
| `IdentityTransformer` | dev passthrough (pixels = mm) until calibration exists | pixels | `RobotCoordinate` | — |
| `HomographyTransformer` | 3x3 planar homography, constant Z; raises `TransformError` on bad matrix/degenerate point | pixels | `RobotCoordinate` | numpy |

## coordinates/calibration.py

| Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|
| `compute_homography(points)` | fit pixel→robot homography (≥4 points, least squares) + reprojection errors; raises `CalibrationError` | `list[CalibrationPoint]` | `CalibrationResult` (matrix, points, rms/max mm) | `cv2.findHomography` |
| `save_calibration(path, result)` | persist matrix/points/errors/timestamp as YAML | Path, `CalibrationResult` | file | yaml |
| `load_calibration(path)` | read + validate 3×3 matrix; raises `CalibrationError` | Path | ndarray | yaml |
| `load_transformer(path, pick_z)` | HomographyTransformer if calibrated, else IdentityTransformer fallback (warning) | Path, float | `CoordinateTransformer` | `load_calibration` |

## targets/pick_target_manager.py

| Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|
| `PickTargetManager.__init__()` | validate strategy name (nearest/leftmost/rightmost/highest_confidence) | `RobotConfig`, `CoordinateTransformer` | — | — |
| `PickTargetManager.generate_targets()` | dashboard candidate view: transform, bounds-check, strategy-order all detections; per-frame numbering | `DetectionResult` | `list[PickTarget]` | `CoordinateTransformer.image_to_robot()`, `WorkspaceBounds.contains()` |
| `PickTargetManager.select_next()` | dispatch the single best NEW target (skips in-progress/cooldown locations within `dedup_radius_mm`); assigns global target id; one target in flight | `DetectionResult`, optional now | `PickTarget` or `None` | internal suppression state |
| `PickTargetManager.notify_pick_complete()` | robot acknowledged: start `picked_cooldown_s` for the location; re-offer with WARNING if part still there after expiry | target_id, optional now | — | — |
| `PickTargetManager.notify_send_failed()` | release in-progress slot after a failed dispatch | target_id | — | — |
| `PickTargetManager.in_progress_target_id` | id of the target currently being picked (dashboard) | — | int or None | — |

## communication/

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| base.py | `RobotInterface` (ABC) | contract: `connect()`, `send_pick_target(target)`, `get_robot_status()`, `is_robot_ready()`, `publish_detection_count(count)` (optional no-op), `disconnect()` | `PickTarget` | `RobotStatus` | — |
| mock_robot.py | `MockRobot` | dev/test robot; records targets in `.received_targets` and counts in `.last_published_count`, always READY when connected | `PickTarget` | `RobotStatus` | — |
| opcua_server.py | `OpcUaRobotServer` | embedded asyncua OPC UA server in a daemon thread; publishes targets to Objects/VisionSystem nodes, polls PickComplete/TargetRequest handshake, BUSY while a target is unacknowledged; push or request mode from config | `PickTarget`, `OpcUaConfig` | OPC UA nodes / `RobotStatus` | asyncua |
| opcua_server.py | `OpcUaRobotServer.get_communication_info()` | live introspection: connect URLs, namespace, nodes w/ NodeIds + values, transport-level clients, uptime | — | `CommunicationInfo` | asyncua, socket |

## app.py + main.py

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| app.py | `create_detector(type)` | detector factory | type string | `PartDetector` | `OpenCVDetector` |
| app.py | `create_robot(config)` | robot communication factory (mock/opcua from communication.yaml; asyncua imported lazily) | `AppConfig` | `RobotInterface` | `MockRobot` / `OpcUaRobotServer` |
| app.py | `VisionApplication.start()` | load references, configure detector, start camera, connect robot | — | — | `load_reference_set`, `CameraManager.start`, `RobotInterface.connect` |
| app.py | `VisionApplication.process_one_frame()` | one full pipeline pass; publishes count to robot; sends targets only when robot ready; updates fps; publishes annotated frame to LiveState | — | `(DetectionResult, list[PickTarget])` | all pipeline modules, `draw_overlay` |
| app.py | `VisionApplication.run()` | mode-driven loop (LIVE/SINGLE_FRAME/DEBUG); DEBUG shows OpenCV window (Q/ESC quits); guarantees `stop()` | — | — | `process_one_frame` |
| app.py | `VisionApplication.request_stop()` | thread-safe loop exit request | — | — | — |
| main.py | `ApplicationSupervisor` | implements AppControl: runs pipeline, stays alive in ERROR state, rebuilds app with fresh config on restart request | — | — | `VisionApplication`, `load_config` |
| main.py | `main()` | composition root: supervisor + LiveState + webapp wiring, logging setup | — | int exit code | `ApplicationSupervisor.run_forever`, `start_web_server` |

## visualization/overlay.py

| Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|
| `draw_overlay(image, result, targets, fps)` | copy of image annotated with boxes, center crosses, labels, target list, count + fps header; never mutates input | ndarray, `DetectionResult`, optional targets/fps | annotated ndarray | OpenCV drawing |

## web layer: webapp/ (standalone package) + exchange contracts

| File | Function/Class | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| vision_system/models/live_state.py | `LiveState.publish()` | store latest annotated JPEG + status snapshot (thread-safe) | jpeg bytes, `DetectionResult`, targets, `RobotStatus`, fps, pending_target_id | — | — |
| vision_system/models/live_state.py | `LiveState.get_jpeg()` / `get_status()` | read-side snapshot access for frontends | — | bytes / dict | — |
| vision_system/app_control.py | `AppControl` (ABC) | frontend → supervisor contract: `get_status()`, `mark_restart_required()`, `request_restart()`, `get_communication_info()` | — | `PipelineStatus` / `CommunicationInfo` | — |
| webapp/server.py | `create_app(state, control)` | FastAPI app: pages (/, /config, /communication) + routers | `LiveState`, `AppControl` | `FastAPI` | routers |
| webapp/server.py | `start_web_server(state, config, control)` | run uvicorn in a daemon thread | + `SystemConfig` | `Thread` | uvicorn |
| webapp/routers/live.py | `make_live_router(state)` | `/api/status` JSON, `/stream` MJPEG (15 fps) | `LiveState` | `APIRouter` | — |
| webapp/routers/config_editor.py | `make_config_router(control, config_dir)` | `GET /api/config` (raw+values), `GET /api/config/schema` (from dataclasses), `POST /api/config/{name}` (validate → atomic write + .bak → restart-required) | `AppControl`, Path | `APIRouter` | `validate_config_data` |
| webapp/routers/config_editor.py | `make_system_router(control)` | `GET /api/system` status, `POST /api/system/restart` | `AppControl` | `APIRouter` | — |
| webapp/routers/communication.py | `make_communication_router(control)` | `GET /api/communication`: live OPC UA introspection or not-running info | `AppControl` | `APIRouter` | `get_communication_info` |

## utils/

| File | Function | Purpose | Input | Output |
|---|---|---|---|---|
| paths.py | `PROJECT_ROOT`, `CONFIG_DIR`, … | canonical project paths (never CWD-relative) | — | `Path` constants |
| paths.py | `resolve(path)` | make relative paths project-root-based | str/Path | `Path` |
| logging_setup.py | `setup_logging(level, log_dir)` | console + rotating file logging | level, dir | — |

## scripts/ (dev tools, not part of the runtime package)

| File | Function | Purpose | Input | Output | Calls |
|---|---|---|---|---|---|
| camera_check.py | `run_preview()` | live preview window with FPS overlay; S saves, Q/ESC quits | `CameraManager`, out dir | frames in `logs/camera_check/` | `CameraManager.get_frame`, OpenCV |
| camera_check.py | `run_headless()` | save N frames + log properties without a window | `CameraManager`, out dir, count | saved JPGs | `CameraManager.get_frame` |
| camera_check.py | `list_cameras()` | probe all USB cameras, save one snapshot each to logs/camera_check/ | out dir | snapshots + log table | `enumerate_usb_cameras` |
| detect_check.py | `main()` | run configured detector on reference images / given files / one live frame; save annotated results to logs/detect_check/ | image paths or `--live` | annotated JPGs + log | detector, `draw_overlay`, `CameraManager` |
| detect_check.py | `run_stability()` | detect over N live frames; log counts, histogram, stability % | detector, config, out dir, N | stability report + last annotated frame | `CameraManager.get_frame`, detector |
| calibrate.py | `collect_points_interactive()` | live window: click markers, prompt robot X/Y per point | config | `list[CalibrationPoint]` | `CameraManager`, OpenCV UI |
| calibrate.py | `main()` | compute + save calibration; `--from-file` headless; `--verify` reprojection | args, config | calibration YAML + error report | `compute_homography`, `save_calibration` |
| opcua_check.py | `main()` | standalone OPC UA server liveness test (no camera): publishes dummy targets on request; for UaExpert/robot-client validation | config | running server until Ctrl+C | `OpcUaRobotServer` |
