# Vision System for Delta Robot Pick-and-Place

A modular Python vision system that captures a live USB camera stream, detects
configured target parts, counts them, extracts their coordinates, transforms
them into robot coordinates, and exposes pick targets to a Delta robot via
OPC UA.

## What It Does

```
Camera → Detection → Counting → Pixel Coordinates → Robot Coordinates → Pick Targets → Delta Robot
```

The target part is defined by **reference images** in `parts/<part_name>/` and
selected in `config/vision.yaml` — no code change is needed to switch parts.

## Quick Start

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Run tests (no hardware required)
pytest -m "not hardware"
```

## Requirements

- Python 3.11+
- USB webcam (development runs without a robot using the mock interface)
- Reference images in `parts/<active_part>/`
- See [CONFIGURATION.md](CONFIGURATION.md) for all settings

## Project Layout

| Path | Purpose |
|---|---|
| `main.py` | Application entry point |
| `src/vision_system/` | All source code (modular packages) |
| `config/` | YAML configuration (camera, vision, robot, system) |
| `parts/` | Reference part datasets (swappable detection targets) |
| `calibration/` | Camera-to-robot calibration data |
| `logs/` | Rotating application logs |
| `tests/` | Unit tests (hardware tests marked `hardware`) |
| `docs_camera/` | This documentation |

## Documentation Map

| Document | Read it for |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module layout and design principles |
| [DATA_FLOW.md](DATA_FLOW.md) | How data travels between modules |
| [FILE_FUNCTION_REFERENCE.md](FILE_FUNCTION_REFERENCE.md) | Every file/function, inputs/outputs |
| [CONFIGURATION.md](CONFIGURATION.md) | Every configuration parameter |
| [CAMERA_INTEGRATION.md](CAMERA_INTEGRATION.md) | Camera abstraction and frame acquisition |
| [VISION_PIPELINE.md](VISION_PIPELINE.md) | Processing modes and detection pipeline |
| [COORDINATE_SYSTEM.md](COORDINATE_SYSTEM.md) | Coordinate conventions and calibration |
| [ROBOT_INTERFACE.md](ROBOT_INTERFACE.md) | Robot communication (OPC UA plan) |
| [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md) | Rules for AI tools modifying this project |
| [MILESTONES.md](MILESTONES.md) | Development plan and current status |
| [CHANGELOG.md](CHANGELOG.md) | Change history with reasons |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common problems and fixes |
