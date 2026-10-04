# Changelog

All meaningful project changes, newest first. Every entry must state the
reason, not only what changed.

## 2026-10-03 (Milestones 15 + 16)

### Added
- `CommunicationInfo`/`NodeInfo`/`ClientInfo` dataclasses in `app_control.py`;
  `AppControl.get_communication_info()` (default None) wired through
  supervisor → `VisionApplication` → `RobotInterface`.
- `OpcUaRobotServer.get_communication_info()`: live introspection — bind
  endpoint, connectable URLs per network interface (resolves the 0.0.0.0
  confusion), namespace + index, mode, uptime, per-node browse name / actual
  NodeId / type / writer / live value, and connected clients from asyncua's
  transport list (peer addresses).
- `GET /api/communication` router + full `/communication` dashboard page:
  connection card with copy buttons, live handshake monitor
  (TargetRequest → TargetReady → PickComplete with StatusCode/target/count),
  node table with live values, connected-clients table. Polls at 1 Hz —
  endpoint/port changes appear automatically after restart because all data
  comes from the running server, not the config.

### Reason
- User requirement: a dedicated communication page showing everything needed
  to connect an OPC UA client, who is connected, and the live handshake,
  reflecting config changes dynamically.

### Validated
- 82 tests passing (incl. introspection + client visibility). Live browser
  validation with `interface: opcua`: page showed a real request-mode cycle
  (TargetRequest + TargetReady lit, target T1 at robot coords) and two
  connected clients with addresses.

## 2026-10-03 (Milestone 14)

### Added
- Config editor page at `/config`: file tabs for all 5 YAML files; form view
  generated from `/api/config/schema` (typed inputs, defaults shown, nested
  workspace/opcua sections); raw YAML tab (preserves comments — form save
  rewrites without them); save → "Restart required" banner + activated
  Restart button (confirm dialog); live pipeline state badge polled every 2 s.

### Changed
- `system.web_port` 8000 → 8080: Windows reserved port 8000 in a TCP excluded
  port range (bind failed with winerror 10013).

### Validated
- Live full cycle on port 8080: form save → restart_required=True → restart →
  clean pipeline teardown/rebuild with fresh config → running, flag cleared.
  Page visually verified in browser (tabs, nested sections, disabled restart
  button while running). 80 tests passing.

## 2026-10-03 (Milestone 13)

### Added
- `src/webapp/`: standalone web frontend package (FastAPI factory, routers
  for live view and config API, static pages with navigation shell).
  Dependency rule enforced by test: vision_system never imports webapp.
- `vision_system/app_control.py`: `AppControl` contract + `PipelineStatus`.
- `ApplicationSupervisor` in `main.py`: runs the pipeline, keeps the web
  server alive in ERROR state on pipeline failures, rebuilds the application
  with freshly loaded config on web-triggered restart.
- Config API: `GET /api/config`, `GET /api/config/schema` (generated from the
  config dataclasses), `POST /api/config/{file}` (raw YAML or values;
  validated via `validate_config_data()`, atomic write with `.yaml.bak`
  backup, sets restart-required), `GET /api/system`, `POST /api/system/restart`.
- `validate_config_data()` + `CONFIG_FILES` registry in `config/loader.py`.

### Changed
- `vision_system/web/` dissolved: `LiveState` moved to
  `vision_system/models/live_state.py` (neutral exchange contract); server and
  static files moved to `webapp/`.

### Reason
- User requirement: web functionality must not be intertwined with the vision
  code — separate package under src/ exchanging data only via common models
  (LiveState, AppControl, dataclasses), so future web growth (config editor,
  communication dashboard) cannot leak into the pipeline.

### Validated
- 80 tests passing incl. 10 new config-API tests and the import-boundary
  guard; vision_system verified to import standalone.

## 2026-10-03 (Milestone 11 software integration)

### Added
- `camera/replay_camera.py`: `ReplayCamera` (camera.type `replay`,
  `camera.replay_dir`) serving image files through `CameraInterface` — enables
  pipeline runs and CI without hardware.
- `scripts/opcua_check.py`: standalone OPC UA server liveness test (no camera);
  used to validate the server against UaExpert (connected, full
  TargetRequest/PickComplete handshake cycled OK).
- `tests/test_end_to_end.py`: automated full-chain test — replay camera →
  detector (synthetic refs) → transformer → dedup target manager → OPC UA
  server in request mode ← asyncua client as robot: request → nearest target
  published → stable during pick → acknowledge → cooldown → next request gets
  the other part.

### Reason
- Milestone 11: validate the complete integration path while the physical
  camera is disconnected; the hardware run later only changes config
  (camera.type usb, interface opcua).

### Validated
- 70 tests passing. UaExpert connected via opc.tcp://localhost:5000
  (0.0.0.0 is the bind address, not a client URL — see TROUBLESHOOTING).

## 2026-10-03 (Milestone 9 + M8 validation)

### Added
- Cross-frame duplicate suppression in `PickTargetManager`: detections are
  matched to previously dispatched targets by robot-space proximity
  (`dedup_radius_mm`). Lifecycle: dispatched target = IN_PROGRESS (location
  suppressed) → `notify_pick_complete()` → cooldown (`picked_cooldown_s`) →
  location free; a part still present after cooldown is re-offered with a
  WARNING (failed pick).
- `select_next()`: single-target dispatch (one target in flight, matching the
  robot's one-request/one-target handshake); `notify_send_failed()` releases
  the slot for retry. `generate_targets()` is now the dashboard candidate
  view with per-frame numbering.
- App polls `get_robot_status().last_pick_target_id` to feed pick
  acknowledgements back into the manager.
- Dashboard shows the in-flight target (`pending_target_id`).

### Changed
- `app.process_one_frame()` no longer tries to send every candidate each
  frame — exactly one new target is dispatched when the robot is ready.

### Reason
- Milestone 9: a stationary part must be offered exactly once; re-offering
  during a pick or before the part is physically removed would cause double
  picks with the request-driven robot.

### Validated
- 69 tests passing, including the full lifecycle (suppression while in
  progress, cooldown, failed-pick re-offer, send-failure retry).
- Milestone 8 marked done: user validated real-world pixel→robot conversion;
  calibration accuracy optimization (RMS 3.49 mm) deferred to a future
  calibrate.py run.

## 2026-09-17 (communication config + request mode)

### Added
- `config/communication.yaml`: all communication parameters (interface
  selection, OPC UA endpoint/namespace/mode/timeouts) — nothing hardcoded in
  the server anymore. New `CommunicationConfig`/`OpcUaConfig` models.
- `TargetRequest` node (Boolean) + `opcua.mode: request`: robot-initiated
  handshake — vision publishes a target only after the robot sets
  TargetRequest; vision resets it on publish. `push` mode keeps the previous
  behaviour. Shipped default deployment config uses `request`.

### Changed
- `robot.yaml` now contains only pick/strategy/workspace settings;
  `interface` and OPC UA fields moved to `communication.yaml`.
- `OpcUaRobotServer` takes `OpcUaConfig`; poll/startup/call timeouts come
  from config.

### Reason
- User requirements: communication parameters must be configurable in a
  dedicated file (more protocols/parameters to come), and the robot works as
  master that requests target data, so target publication must be
  request-driven.

### Validated
- 62 tests passing, including a full request-mode cycle over a real localhost
  OPC UA connection (request → publish → pick → acknowledge → await next request).

## 2026-09-05 (Milestone 10)

### Added
- `communication/opcua_server.py`: `OpcUaRobotServer` — embedded asyncua OPC
  UA server (vision board = server, robot = polling client) on
  `opc.tcp://0.0.0.0:5000`. Nodes under Objects/VisionSystem: TargetX/Y/Z
  (Double), TargetId/DetectedCount/StatusCode (Int32), TargetReady/
  PickComplete (Boolean) — no String nodes (robot supports Bool/Int/Real
  only). Pick handshake: TargetReady=True → robot writes PickComplete=True →
  server resets flags. NoSecurity policy + NodeId 2735/2267 compatibility
  writes taken from the user's validated server.
- `RobotInterface.publish_detection_count()` (optional, default no-op);
  called each frame, OPC UA writes only on change.
- 7 integration tests using `asyncua.sync.Client` as a simulated robot.

### Changed
- Package restructure: `robot/` → `communication/` — protocol implementations
  are now clearly separated from vision processing; future protocols (Modbus
  etc.) are additional modules in `communication/`.
- `create_robot()` factory takes the config and supports `opcua`;
  `robot.opcua_endpoint` default changed to port 5000.

### Reason
- User decision: communication is a separate concern from image processing
  and more protocols may follow. Server/client roles, port 5000, type
  constraints, and compatibility node writes confirmed against the user's
  working OPC UA server and robot client.

### Validated
- 59 unit/integration tests passing, including full pick handshake over a
  real localhost OPC UA connection.

## 2026-09-05 (Milestone 7 tooling)

### Added
- `coordinates/calibration.py`: `compute_homography()` (≥4 points,
  least-squares, reprojection RMS/max error in mm), `save_calibration()` /
  `load_calibration()` (YAML with matrix, points, errors, timestamp),
  `load_transformer()` (HomographyTransformer when calibrated,
  IdentityTransformer fallback with warning).
- `scripts/calibrate.py`: interactive click-to-calibrate live window
  (U undo, ENTER done, per-point robot X/Y prompts), headless `--from-file
  points.yaml`, and `--verify` reprojection check. Warns above 2 mm RMS.
- 8 calibration unit tests (recovery of known transform, degenerate/short
  input rejection, persistence round-trip, transformer fallback).

### Changed
- `VisionApplication` now loads the coordinate transformer via
  `load_transformer()` at startup instead of always using
  IdentityTransformer.

### Reason
- Milestone 7: the calibration procedure and persistence must exist and be
  testable independently of the physical setup; the physical calibration run
  happens once the camera has its final top-down mount and robot coordinates
  for the markers are known.

## 2026-09-05 (confidence recalibration)

### Fixed
- Bracket part not detected in the live stream: live frames carry motion blur
  and slight tilt, giving Hu shape distances of 0.10–0.16 against the crisp
  references — confidence fell just below the 0.6 threshold. `match_scale`
  default lowered 10 → 3 so same-part live variation (d ≤ ~0.22) passes while
  cross-class shapes (d ≥ 0.3, measured: disc↔bracket, clutter d ≈ 4.7)
  remain rejected.

### Validated
- Live bracket: 30/30 frames count = 1 (100% stable), conf 0.65, correct box.
- Cross-class: bracket detector on round images still 0 detections.
- 44 unit tests passing.

## 2026-09-05 (Milestone 6)

### Fixed
- Reference shape extraction no longer picks background clutter: contours
  touching the image border are excluded (a valid reference part must be
  fully visible). Found when the bracket references all contained the same
  bright object at the frame edge, which self-matched at confidence 1.0.
- New `detection_params.min_reference_area_fraction` (default 0.01): a
  reference part must fill ≥1% of its image, rejecting tiny noise blobs that
  previously poisoned the area bounds.

### Changed
- Reference-quality warnings now say what to do ("recapture with the part
  fully in view / closer").

### Reason
- Milestone 6 validation with a second real part class (braket_part, 6
  images) exposed both weaknesses; the detector must be robust against
  imperfect reference captures since users provide them.

### Validated
- Switching `vision.active_part` round_part↔braket_part (config only, no code):
  bracket refs detect bracket (conf 1.0, correct box), round detector rejects
  bracket images (0 detections) and vice versa. Round set: 20/23 usable with
  actionable warnings for the 3 flagged captures. 44 unit tests passing.

## 2026-09-05 (Milestone 5)

### Added
- `scripts/detect_check.py --live --frames N`: count-stability mode — detects
  over N consecutive live frames and reports the per-frame counts, histogram,
  and dominant-count stability percentage.

### Reason
- Milestone 5 requires proving the count is reliable over time, not just on a
  single frame.

### Validated
- 3 physical parts in view: count = 3 in 30/30 frames (100% stable),
  confidences 1.00/1.00/0.79 (lowest = part clipped by the frame edge —
  correct behaviour). Bright background clutter rejected by shape/area filters.

## 2026-09-05 (Milestone 4)

### Added
- `OpenCVDetector` full implementation: grayscale → blur → Otsu/fixed
  threshold → morphology → external contours → area-fraction filter (bounds
  derived from reference images) → Hu-moment shape matching
  (`cv2.matchShapes`); confidence = 1/(1 + match_scale·distance).
- `vision.detection_params` tunables: blur_kernel, threshold, invert,
  morph_kernel, area_tolerance, min_area_px, match_scale.
- `scripts/detect_check.py`: run the configured detector on reference images,
  arbitrary files, or one live frame; saves annotated output.
- `camera.warmup_frames` (default 5): discards frames after open so
  auto-exposure settles (first DirectShow frame was black).
- Synthetic-image detector tests (circles/bars, scale invariance, invert mode).

### Changed
- `PartDetector.configure()` interface: added optional `params` argument
  (implementation-specific tuning). All implementations and callers updated.
- `config/camera.yaml` `device_index: 1 → 0`: Windows re-enumerated the
  devices; index 0 is now the external workspace camera.

### Reason
- Milestone 4. Contour + Hu-moment matching is scale/rotation invariant,
  needs no training, and fits the confirmed setup (shiny part, dark
  workspace). Area bounds derived from references make the detector adapt to
  any part dataset without code changes.

### Validated
- 23/23 real reference images: exactly 1 detection each, conf = 1.000, no
  false positives from background clutter.
- Live frame: 1 detection, conf 0.999, center/box visually verified.
- 45 tests passing.

## 2026-08-19 (camera backend fix)

### Added
- `camera.backend` config parameter (`auto`/`dshow`/`msmf`/`v4l2`) applied in
  `USBCamera.open()`, plus an "Opening camera ..." log line so slow opens are
  visible.

### Fixed
- Application appeared stuck after "OpenCVDetector configured": OpenCV's
  default MSMF backend on Windows took minutes to open the external USB
  camera. DirectShow (`backend: dshow`) opens it in ~3 s (verified).

### Reason
- Known OpenCV/Windows MSMF issue with some UVC cameras; backend must be
  selectable per platform (Linux deploy will use `auto`/`v4l2`).

## 2026-08-19 (camera selection)

### Added
- `enumerate_usb_cameras()` in `camera/usb_camera.py`: probes device indices
  (DirectShow) and returns resolution + optional snapshot per camera.
- `scripts/camera_check.py --list` (snapshot per device) and `--device IDX`
  (preview a specific index).

### Changed
- `config/camera.yaml` `device_index: 0 → 1`: probing found three devices —
  0 = built-in webcam, 1 = external USB camera, 2 = virtual screen-capture
  device. The user selected device 1 for the vision process.

### Reason
- Systems with multiple (including virtual) cameras need a reliable way to
  identify and select the correct physical camera without trial and error.

## 2026-08-19 (Milestone 3)

### Added
- `visualization/overlay.py`: `draw_overlay()` renders bounding boxes, center
  markers, pixel coordinates, target list, part count, and FPS onto frames.
- `web/` package: `LiveState` (thread-safe pipeline snapshot), FastAPI server
  (`/` dashboard, `/stream` MJPEG, `/api/status` JSON), static dashboard page,
  `start_web_server()` running uvicorn in a daemon thread.
- `VisionApplication`: FPS measurement, per-frame publishing to `LiveState`
  (JPEG-encoded annotated frame), DEBUG-mode OpenCV window (Q/ESC quits),
  `request_stop()` for thread-safe shutdown.
- Tests: overlay renderer, `LiveState`, web endpoints (`httpx` test dep added).

### Changed
- `main.py` starts the web server (when `system.web_enabled`) and injects
  `LiveState` into the application.

### Reason
- Milestone 3 requires a stable continuous pipeline with visual feedback. The
  web layer only reads a published snapshot, keeping vision processing fully
  decoupled from presentation.

### Validated
- Live run: ~30 fps at 1280×720, `/api/status` and MJPEG stream verified
  against the running system with the mock robot connected.

## 2026-08-19

### Added
- `tests/test_camera_hardware.py`: hardware-marked smoke tests (open/stream,
  frame structure, monotonic frame ids, non-blank signal).
- `scripts/camera_check.py`: Milestone 2 validation tool — live preview with
  FPS overlay (S saves a frame, Q/ESC quits) and headless `--save N` mode;
  frames written to `logs/camera_check/`.

### Changed
- Milestone 2 marked done: real USB camera validated at 1280×720 BGR,
  4/4 hardware tests passing, sample frames visually verified.

### Reason
- Milestone 2 requires proving stable acquisition on real hardware, separate
  from the unit tests that use a fake driver.

## 2026-08-13

### Added
- Initial project skeleton (Milestone 1): package `src/vision_system/` with
  `models/data.py` (all shared dataclasses/enums), camera abstraction
  (`CameraInterface`, `USBCamera`, `CameraManager` with reconnect policy),
  image processor (pass-through), detector abstraction (`PartDetector`,
  `OpenCVDetector` skeleton, reference-set loader/validation), coordinate
  transformers (`IdentityTransformer`, `HomographyTransformer`),
  `PickTargetManager` (strategies: nearest/leftmost/rightmost/
  highest_confidence + workspace bounds check), robot abstraction
  (`RobotInterface`, `MockRobot`), orchestrator `VisionApplication`, entry
  point `main.py`.
- Typed YAML configuration system (`config/*.yaml` → `AppConfig`), rejecting
  unknown keys.
- Test suite: config loader, camera manager (FakeCamera), detector/reference
  loader, coordinate transforms, target manager, robot interface contract.
- Full `docs_camera/` documentation set.
- Project meta: `pyproject.toml` (pytest config, `hardware` marker),
  `requirements.txt`, `.gitignore`, `parts/` dataset structure.

### Reason
- Establish the modular architecture and typed interfaces first (per project
  brief) so that later milestones can implement detection, calibration, and
  OPC UA communication without restructuring. Hardware-independent layers are
  fully testable from day one.
