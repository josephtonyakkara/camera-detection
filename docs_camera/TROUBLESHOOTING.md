# Troubleshooting

## Startup

| Symptom | Likely cause | Fix |
|---|---|---|
| Web server fails: `winerror 10013` binding the port | port is in a Windows excluded/reserved TCP range (check `netsh interface ipv4 show excludedportrange protocol=tcp`) | pick another `system.web_port` (e.g. 8080) |
| `ConfigError: Unknown keys in camera.yaml: [...]` | typo in a YAML key | compare against CONFIGURATION.md |
| `ConfigError: Invalid YAML in ...` | YAML syntax error | validate indentation/quotes |
| `ReferenceDataError: Reference folder not found ... Available parts: [...]` | `vision.active_part` doesn't match a folder in `parts/` | create the folder or fix `active_part` (message lists valid options) |
| `ReferenceDataError: No reference images in ...` | part folder empty or wrong extensions | add `.jpg/.jpeg/.png/.bmp` files |
| `ModuleNotFoundError: vision_system` | venv not active or run outside project | activate `.venv`, run `python main.py` from project root |

## Camera

| Symptom | Likely cause | Fix |
|---|---|---|
| `CameraError: Cannot open USB camera at index 0` | wrong index, camera in use, no permission | try other `device_index` values; close apps using the camera; on Linux check `/dev/video*` permissions |
| Startup hangs after "OpenCVDetector configured" (camera never opens) | Windows MSMF backend stalls opening some external USB cameras | set `backend: dshow` in `config/camera.yaml` |
| `CameraError: Unknown camera backend '...'` | typo in `backend` | use `auto`, `dshow`, `msmf`, or `v4l2` |
| `CameraError: Camera could not be started` after retries | camera unplugged/faulty | check connection; increase `reconnect_attempts` |
| Wrong resolution in frames | driver ignored requested size | `FrameData.width/height` reflect reality; adjust `camera.yaml` to a supported mode |
| Frame acquisition intermittently fails | flaky USB connection | manager auto-reconnects once per call; check cable/hub if persistent |

## Detection

| Symptom | Likely cause | Fix |
|---|---|---|
| `DetectorError: Detector not configured` | `detect()` called before `configure()` | use `VisionApplication` which wires this, or call `configure()` in custom code |
| `DetectorError: No usable part contour found in any reference image` | references too dark/blurry, part not distinguishable from background, part touching image border in every photo, or part too small in frame | recapture references with the part fully in view and closer; try `detection_params.invert` or a fixed `threshold` |
| "Reference ...: all contours touch the image border" warning | part (or only bright object) clipped by frame edge in that photo | recapture that reference with the part fully inside the view |
| "largest fully-visible contour too small" warning | part too far from camera or only noise visible | recapture closer, or lower `min_reference_area_fraction` |
| Always 0 detections | part/background contrast too low, area bounds too tight, or threshold too high | run `scripts/detect_check.py --live`, inspect annotated output; raise `area_tolerance`, lower `confidence_threshold` |
| Part detected on reference images but not live | live blur/tilt raises shape distance; confidence just under threshold | lower `detection_params.match_scale` (e.g. 3) or `confidence_threshold`; improve lighting/focus |
| Black frames / 0 detections right after start | auto-exposure not settled | increase `camera.warmup_frames` |
| Two parts detected as one | parts touching each other or another bright object | separate parts; keep workspace background clear |
| Wrong-shape objects detected | confidence threshold too low | raise `vision.confidence_threshold` or `match_scale` |

## Targets / Robot

| Symptom | Likely cause | Fix |
|---|---|---|
| UA client cannot connect to `opc.tcp://0.0.0.0:5000` | `0.0.0.0` is the server bind address, not a destination | connect to `opc.tcp://localhost:5000` (same PC) or `opc.tcp://<board-ip>:5000`; allow port 5000 through the firewall for remote clients |
| `Rejecting target outside workspace` warnings | calibration wrong or workspace bounds too tight | verify calibration (M7); check `robot.yaml` workspace values |
| `Robot not ready; target N not sent` | robot busy/disconnected | expected behaviour; target is regenerated on later frames |
| `NotImplementedError: OPC UA interface ...` | `robot.interface: opcua` before Milestone 10 | use `interface: mock` until M10 |

## Tests

| Symptom | Likely cause | Fix |
|---|---|---|
| Hardware tests fail on CI/dev machine | no camera attached | run `pytest -m "not hardware"` |
