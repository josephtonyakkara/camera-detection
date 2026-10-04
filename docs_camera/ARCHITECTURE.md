# Architecture

## Layering Principle

```
Hardware  →  Hardware abstraction  →  Processing  →  Business logic  →  Communication
(camera)     (CameraInterface)        (processor,    (target manager)   (RobotInterface)
                                       detector)
```

Strict rules:
- The camera does not know a robot exists.
- The detector does not know which communication protocol the robot uses.
- The robot interface does not know how images were processed.
- Modules communicate only through the typed data models in `models/data.py`.

## Module Map

```
src/
├── vision_system/             the processing application (runs headless without webapp)
│   ├── app.py                 Orchestrator: wires modules, owns the processing loop
│   ├── app_control.py         AppControl contract + PipelineStatus (webapp → supervisor commands)
│   ├── config/                YAML loading → typed AppConfig dataclasses + validation helpers
│   ├── camera/                CameraInterface, USB/replay drivers, manager
│   ├── processing/            FrameData → ProcessedFrame
│   ├── detection/             PartDetector, OpenCV implementation, reference loader
│   ├── coordinates/           transformers + homography calibration
│   ├── targets/               PickTargetManager (dedup lifecycle)
│   ├── communication/         RobotInterface, mock, OPC UA server
│   ├── models/
│   │   ├── data.py            shared dataclasses (exchange contract)
│   │   └── live_state.py      LiveState: pipeline publishes, frontends read
│   ├── visualization/         overlay renderer (pipeline-side drawing)
│   └── utils/                 paths, logging
└── webapp/                    standalone web frontend — NEVER imported by vision_system
    ├── server.py              FastAPI factory + uvicorn daemon thread
    ├── routers/
    │   ├── live.py            /stream (MJPEG), /api/status
    │   └── config_editor.py   /api/config (read/validate/save), /api/system (+restart)
    └── static/                index.html, config.html, communication.html

main.py                        composition root: supervisor (implements AppControl),
                               injects LiveState + control into webapp
```

## Package Dependency Rule (enforced by test)

```
webapp ──imports──► vision_system.models / app_control / config.loader     (allowed)
vision_system ──imports──► webapp                                           (FORBIDDEN)
```

Data exchange happens only through neutral contracts: `LiveState`
(pipeline → frontend), `AppControl` (frontend → supervisor), and the
dataclasses in `models/`. `tests/test_config_api.py` fails if vision_system
ever imports webapp; deleting `src/webapp/` leaves the pipeline fully
functional (headless).

## Replaceability

Each abstraction allows swapping implementations without touching consumers:

| To replace | Implement | Register in |
|---|---|---|
| Camera hardware | `CameraInterface` | `camera/manager.py:create_camera()` |
| Detection method (e.g. YOLO) | `PartDetector` | `app.py:create_detector()` |
| Calibration method | `CoordinateTransformer` | `app.py` (transformer injection) |
| Robot protocol (e.g. OPC UA → Modbus) | `RobotInterface` in `communication/` | `app.py:create_robot()` |

## Runtime Composition

`VisionApplication` (in `app.py`) is the only place where concrete
implementations are chosen, driven entirely by configuration. All other
modules receive their dependencies via constructor injection, which keeps
them unit-testable without hardware.

## Planned Extensions (do not restructure for them prematurely)

- `coordinates/calibration.py` physical calibration run (tooling exists, M7)
- Additional protocols (e.g. Modbus) as new modules in `communication/`

## Web Layer Decoupling

The pipeline thread publishes an annotated JPEG + status snapshot into
`LiveState` after each frame; FastAPI handlers only read that snapshot. The
web server runs in a daemon thread started by `main.py` and holds no
references to camera, detector, or robot objects.
