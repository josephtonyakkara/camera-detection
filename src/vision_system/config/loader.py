"""Loads YAML configuration files into typed AppConfig objects."""

from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

import yaml

from vision_system.config.models import (
    AppConfig,
    CameraConfig,
    CommunicationConfig,
    OpcUaConfig,
    RobotConfig,
    SystemConfig,
    VisionConfig,
    WorkspaceBounds,
)
from vision_system.utils.paths import CONFIG_DIR

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConfigError(Exception):
    """Raised when configuration files are invalid."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Config file %s not found; using defaults", path.name)
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at top level")
    return data


def _build(cls: type[T], data: dict[str, Any], source: str) -> T:
    """Instantiate a config dataclass, rejecting unknown keys."""
    known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
    unknown = set(data) - known
    if unknown:
        raise ConfigError(f"Unknown keys in {source}: {sorted(unknown)}")
    return cls(**data)


# config file stem -> (top-level model, {nested key: nested model})
CONFIG_FILES: dict[str, tuple[type, dict[str, type]]] = {
    "camera": (CameraConfig, {}),
    "vision": (VisionConfig, {}),
    "robot": (RobotConfig, {"workspace": WorkspaceBounds}),
    "communication": (CommunicationConfig, {"opcua": OpcUaConfig}),
    "system": (SystemConfig, {}),
}


def validate_config_data(file_name: str, data: dict[str, Any]) -> None:
    """Validate a parsed config mapping against its model.

    Raises:
        ConfigError: unknown file, unknown keys, or invalid structure/types.
    """
    if file_name not in CONFIG_FILES:
        raise ConfigError(f"Unknown config file: {file_name!r}")
    if not isinstance(data, dict):
        raise ConfigError(f"{file_name}.yaml must contain a mapping at top level")
    model, nested = CONFIG_FILES[file_name]
    payload = dict(data)
    for key, nested_model in nested.items():
        nested_data = payload.pop(key, {})
        if not isinstance(nested_data, dict):
            raise ConfigError(f"{file_name}.yaml: {key} must be a mapping")
        _build(nested_model, nested_data, f"{file_name}.yaml:{key}")
    _build(model, payload, f"{file_name}.yaml")


def load_config(config_dir: Path | None = None) -> AppConfig:
    """Load camera/vision/robot/system YAML files from ``config_dir``.

    Missing files fall back to defaults; invalid content raises ConfigError.
    """
    cfg_dir = config_dir or CONFIG_DIR

    robot_data = _read_yaml(cfg_dir / "robot.yaml")
    workspace_data = robot_data.pop("workspace", {})
    robot = _build(RobotConfig, robot_data, "robot.yaml")
    robot.workspace = _build(WorkspaceBounds, workspace_data, "robot.yaml:workspace")

    communication_data = _read_yaml(cfg_dir / "communication.yaml")
    opcua_data = communication_data.pop("opcua", {})
    communication = _build(CommunicationConfig, communication_data, "communication.yaml")
    communication.opcua = _build(OpcUaConfig, opcua_data, "communication.yaml:opcua")

    return AppConfig(
        camera=_build(CameraConfig, _read_yaml(cfg_dir / "camera.yaml"), "camera.yaml"),
        vision=_build(VisionConfig, _read_yaml(cfg_dir / "vision.yaml"), "vision.yaml"),
        robot=robot,
        communication=communication,
        system=_build(SystemConfig, _read_yaml(cfg_dir / "system.yaml"), "system.yaml"),
    )
