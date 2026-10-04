# Camera Integration

## How the Camera Connects to the Backend

```
Physical USB camera
      ↓  USB/UVC
OpenCV VideoCapture (driver/SDK layer)
      ↓
USBCamera (implements CameraInterface)      src/vision_system/camera/usb_camera.py
      ↓
CameraManager (lifecycle + reconnect)       src/vision_system/camera/manager.py
      ↓  FrameData
Vision pipeline (processor → detector)
```

The application never touches OpenCV capture APIs directly — only
`CameraInterface`. Swapping to RealSense/GigE later means adding one driver
class and one factory entry (see ARCHITECTURE.md → Replaceability).

## Lifecycle

| Phase | Behaviour |
|---|---|
| Initialization | `CameraManager.start()` calls `open(config)`; retries `reconnect_attempts` times with `reconnect_delay_s` between attempts; raises `CameraError` after final failure |
| Acquisition | `get_frame()` returns the latest `FrameData`; on read failure the manager closes and reopens the driver once, then re-raises |
| Shutdown | `stop()` → `close()`; idempotent, always safe to call |

## Frame Format

| Property | Value |
|---|---|
| Container | `FrameData` dataclass |
| Image | `numpy.ndarray`, shape `(height, width, 3)` |
| Color format | BGR (OpenCV default) — recorded in `FrameData.color_format` |
| `frame_id` | monotonically increasing per driver instance |
| `timestamp` | `time.time()` at acquisition |
| Resolution/FPS | requested from `config/camera.yaml`; actual values may differ (driver-dependent) — `FrameData.width/height` always reflect the real frame |
| Depth | not available (RGB-only USB camera); a depth-capable driver would extend `FrameData` |

## Error Handling

- Camera absent at startup → retries, then `CameraError("Camera could not be started")`;
  `main.py` logs it and exits with code 1. The application never crashes with a raw traceback.
- Camera unplugged mid-run → `get_frame()` fails → one automatic reconnect attempt →
  persistent failure propagates as `CameraError`.
- All camera events are logged (`Camera started`, `Camera stopped`, reconnect warnings).

## Hardware Test Guidance

Unit tests use a `FakeCamera` (tests/test_camera.py) — no hardware needed.
Live camera smoke tests live in `tests/test_camera_hardware.py`
(`pytest -m hardware`): open/stream, frame structure (shape/dtype/BGR),
monotonic frame ids, non-blank signal.

Manual validation tool:

```bash
python scripts/camera_check.py            # live preview; S saves frame, Q/ESC quits
python scripts/camera_check.py --save 3   # headless: save 3 frames to logs/camera_check/
python scripts/camera_check.py --list     # probe indices 0-9, save one snapshot per camera
python scripts/camera_check.py --device 1 # preview a specific device index
```

## Selecting Among Multiple Cameras

`enumerate_usb_cameras()` (camera/usb_camera.py) probes device indices and
returns resolution + optional snapshot per responding device. Run
`--list`, inspect the snapshots in `logs/camera_check/device_<n>.jpg`, and set
the chosen index as `device_index` in `config/camera.yaml`.
Beware: virtual cameras (screen-capture drivers) can appear as devices — the
snapshot makes them easy to identify.

Validated 2026-08-19: device 1 (external USB camera) selected; delivers
1280×720 BGR as configured.
