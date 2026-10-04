# Configuration

All settings live in `config/*.yaml`, loaded by `config/loader.py` into typed
dataclasses (`config/models.py`). Missing files fall back to defaults; unknown
keys and invalid YAML raise `ConfigError` at startup.

Relative paths are resolved against the **project root**, never the working
directory.

## config/camera.yaml

| Parameter | Purpose | Example | Required | Used by |
|---|---|---|---|---|
| `type` | camera driver selection | `usb` | no (default `usb`) | `camera/manager.py` factory |
| `device_index` | OpenCV VideoCapture index; discover with `scripts/camera_check.py --list` | `1` | no | `USBCamera` |
| `backend` | capture backend: `auto` / `dshow` / `msmf` / `v4l2`; use `dshow` on Windows (MSMF can hang for minutes opening external cameras) | `dshow` | no (default `auto`) | `USBCamera` |
| `replay_dir` | image folder served as frames when `type: replay` (tests/dev without hardware) | `logs/camera_check` | for `replay` | `ReplayCamera` |
| `width` | requested frame width (px) | `1280` | no | `USBCamera` |
| `height` | requested frame height (px) | `720` | no | `USBCamera` |
| `fps` | requested frame rate | `30` | no | `USBCamera` |
| `warmup_frames` | frames discarded after open (auto-exposure settling; first DirectShow frame can be black) | `5` | no | `USBCamera` |
| `reconnect_attempts` | open retries before giving up | `3` | no | `CameraManager` |
| `reconnect_delay_s` | delay between retries (s) | `2.0` | no | `CameraManager` |

## config/vision.yaml

| Parameter | Purpose | Example | Required | Used by |
|---|---|---|---|---|
| `detector` | detection implementation | `opencv` | no | `app.py` factory |
| `active_part` | folder under `parts_dir` defining the detection target | `round_part` | **yes** for detection | `reference_loader.py` |
| `parts_dir` | reference dataset root | `parts` | no | `reference_loader.py` |
| `confidence_threshold` | minimum detection confidence | `0.6` | no | detectors |
| `processing_mode` | `live` / `single_frame` / `debug` | `live` | no | `VisionApplication` |
| `detection_params` | detector-specific tuning map (below) | `{}` | no | detectors |

### detection_params for `detector: opencv`

| Key | Purpose | Default |
|---|---|---|
| `blur_kernel` | Gaussian blur kernel (odd); 0 disables | `5` |
| `threshold` | `otsu` or fixed 0-255 value | `otsu` |
| `invert` | `true` when parts are darker than background | `false` |
| `morph_kernel` | open/close kernel size; 0 disables | `5` |
| `area_tolerance` | widens the reference-derived area-fraction bounds | `2.5` |
| `min_area_px` | absolute noise floor in pixels | `400` |
| `min_reference_area_fraction` | minimum image fraction a reference part must fill | `0.01` |
| `match_scale` | confidence = 1/(1 + match_scale·shape_distance); lower = more tolerant of blur/tilt | `3.0` |

**Switching the target part:** create `parts/<new_part>/` with reference
images and set `active_part: <new_part>`. No code change.

## config/robot.yaml

| Parameter | Purpose | Example | Required | Used by |
|---|---|---|---|---|
| `pick_z` | constant pick height (mm, robot frame) | `-50.0` | **yes** for real picking | `PickTargetManager` |
| `target_selection` | ordering strategy: `nearest` / `leftmost` / `rightmost` / `highest_confidence` | `nearest` | no | `PickTargetManager` |
| `dedup_radius_mm` | detections within this radius are treated as the same physical part | `15.0` | no | `PickTargetManager` |
| `picked_cooldown_s` | suppress a picked location this long (arm retract/part removal) | `3.0` | no | `PickTargetManager` |
| `workspace.x_min/x_max/y_min/y_max` | workspace limits (mm); targets outside are rejected | `±200.0` | **yes** for safety | `PickTargetManager` |

## config/communication.yaml

| Parameter | Purpose | Example | Required | Used by |
|---|---|---|---|---|
| `interface` | robot communication implementation: `mock` / `opcua` | `mock` | no | `app.py` factory |
| `opcua.endpoint` | OPC UA server endpoint (vision board is the server) | `opc.tcp://0.0.0.0:5000` | for `opcua` | `communication/opcua_server.py` |
| `opcua.namespace` | OPC UA namespace URI | `http://camera-detection/vision` | for `opcua` | `communication/opcua_server.py` |
| `opcua.mode` | `request` = robot writes TargetRequest before a target is published; `push` = publish whenever idle | `request` | no (default `push`) | `communication/opcua_server.py` |
| `opcua.handshake_poll_s` | poll interval for PickComplete/TargetRequest | `0.1` | no | `communication/opcua_server.py` |
| `opcua.start_timeout_s` | max wait for server startup | `15.0` | no | `communication/opcua_server.py` |
| `opcua.call_timeout_s` | timeout per node operation | `5.0` | no | `communication/opcua_server.py` |

## config/system.yaml

| Parameter | Purpose | Example | Required | Used by |
|---|---|---|---|---|
| `log_level` | DEBUG/INFO/WARNING/ERROR | `INFO` | no | `logging_setup.py` |
| `log_dir` | log file directory | `logs` | no | `logging_setup.py` |
| `calibration_file` | homography data path | `calibration/homography.yaml` | for M7+ | transformer loading |
| `web_enabled` | enable web dashboard | `true` | no | webapp |
| `web_host` | dashboard bind address | `0.0.0.0` | no | webapp |
| `web_port` | dashboard port (8000 is reserved by Windows on some systems) | `8080` | no | webapp |

All five files can also be edited from the web dashboard at `/config`
(form or raw YAML; validated server-side; changes apply after the restart
button is pressed).

## Infrastructure Checklist

For the full system to run:

1. Python 3.11+ virtual environment with `requirements.txt` installed
2. USB camera connected (device index matches `camera.yaml`)
3. Reference images present in `parts/<active_part>/`
4. `config/*.yaml` present (defaults used for missing files)
5. Calibration file present (Milestone 7+; IdentityTransformer used until then)
6. Robot controller reachable via OPC UA (Milestone 10+; mock used until then)
