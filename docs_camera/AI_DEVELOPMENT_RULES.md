# AI Development Rules

Primary instruction document for AI coding tools working on this project.
Read this before making any change.

## Required Workflow Before Modifying Code

1. Read the relevant `docs_camera/*.md` for the area you are changing.
2. Understand the existing architecture (ARCHITECTURE.md).
3. Identify which module owns the requested functionality
   (FILE_FUNCTION_REFERENCE.md).
4. Check whether the functionality already exists — do not duplicate.
5. Modify the **smallest appropriate module**.
6. Check whether any interface (ABC, dataclass, config key) changed.
7. Update the affected documentation (see "Documentation Sync" below).
8. Add an entry to CHANGELOG.md with the **reason** for the change.
9. Explain any architectural change explicitly.

Do **not** restructure unrelated parts of the project because a different
architecture seems better. Do **not** silently change existing interfaces.

## Architecture Rules

- Keep modules independent; communicate only via the dataclasses in `models/data.py`.
- **Package boundary**: `webapp` may import `vision_system.models`,
  `vision_system.app_control`, and `vision_system.config.loader`;
  `vision_system` must NEVER import `webapp` (enforced by
  `tests/test_config_api.py::test_vision_system_never_imports_webapp`).
  Composition happens only in `main.py`.
- Camera drivers contain no detection, coordinate, or robot logic.
- Detectors contain no camera, calibration, or robot logic.
- The robot interface contains no image-processing logic.
- New camera / detector / transformer / robot implementations implement the
  existing ABC and are registered in the corresponding factory
  (`camera/manager.py:create_camera`, `app.py:create_detector`, `app.py:create_robot`).
- Prefer configuration over hardcoded values; new tunables go into
  `config/*.yaml` + `config/models.py` + CONFIGURATION.md.
- Avoid unnecessarily large files; split by responsibility.
- Concrete implementations are chosen only in `app.py` / factories, driven by config.

## Code Rules

- Python 3.11+, type hints on all public functions and dataclass fields.
- Docstrings on public classes and non-obvious public functions.
- Use module-level `logging.getLogger(__name__)`; never `print()` for diagnostics.
- No excessive logging inside the per-frame loop (use DEBUG level there).
- Raise the module's specific exception type (`CameraError`, `DetectorError`,
  `TransformError`, `RobotError`, `ConfigError`, `ReferenceDataError`);
  handle exceptions explicitly at the orchestration layer.
- No global mutable state; dependencies are constructor-injected.
- Resolve paths via `utils/paths.py`, never via the current working directory.
- Zero detections is a valid result, never an exception.

## Testing Rules

- Every module change updates/extends its tests in `tests/`.
- Hardware-dependent tests carry `@pytest.mark.hardware`; the default suite
  (`pytest -m "not hardware"`) must pass without camera or robot attached.
- Test doubles (e.g. `FakeCamera`) implement the real ABCs.

## Documentation Sync

When a change touches any of the following, update the listed files **in the
same change**:

| Change | Update |
|---|---|
| Any code change worth recording | CHANGELOG.md (with reason) |
| Files/functions/classes added, removed, re-signatured | FILE_FUNCTION_REFERENCE.md |
| Module structure, layering, factories | ARCHITECTURE.md |
| Data models or module-to-module handoffs | DATA_FLOW.md |
| Config keys | CONFIGURATION.md + the YAML file comment |
| Camera behaviour/drivers | CAMERA_INTEGRATION.md |
| Detection/processing behaviour | VISION_PIPELINE.md |
| Coordinate conventions/calibration | COORDINATE_SYSTEM.md |
| Robot communication | ROBOT_INTERFACE.md |
| Milestone progress | MILESTONES.md (status column) |
| New failure modes | TROUBLESHOOTING.md |

Documentation must always reflect the current state of the code.
