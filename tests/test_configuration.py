"""Tests for the YAML configuration loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from vision_system.config.loader import ConfigError, load_config


def test_defaults_when_files_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.camera.type == "usb"
    assert cfg.vision.active_part == "round_part"
    assert cfg.communication.interface == "mock"
    assert cfg.communication.opcua.mode == "push"
    assert cfg.communication.opcua.endpoint.endswith(":5000")
    assert cfg.system.log_level == "INFO"


def test_loads_values_from_yaml(tmp_path: Path) -> None:
    (tmp_path / "vision.yaml").write_text("active_part: square_part\nconfidence_threshold: 0.8\n")
    (tmp_path / "robot.yaml").write_text(
        "pick_z: -42.0\nworkspace:\n  x_min: -10\n  x_max: 10\n"
    )
    (tmp_path / "communication.yaml").write_text(
        "interface: opcua\nopcua:\n  endpoint: opc.tcp://0.0.0.0:5099\n  mode: request\n"
        "  handshake_poll_s: 0.05\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.vision.active_part == "square_part"
    assert cfg.vision.confidence_threshold == 0.8
    assert cfg.robot.pick_z == -42.0
    assert cfg.robot.workspace.x_min == -10
    assert cfg.robot.workspace.contains(5, 0)
    assert not cfg.robot.workspace.contains(11, 0)
    assert cfg.communication.interface == "opcua"
    assert cfg.communication.opcua.endpoint == "opc.tcp://0.0.0.0:5099"
    assert cfg.communication.opcua.mode == "request"
    assert cfg.communication.opcua.handshake_poll_s == 0.05


def test_unknown_communication_key_rejected(tmp_path: Path) -> None:
    (tmp_path / "communication.yaml").write_text("opcua:\n  portt: 5000\n")
    with pytest.raises(ConfigError, match="portt"):
        load_config(tmp_path)


def test_unknown_key_rejected(tmp_path: Path) -> None:
    (tmp_path / "camera.yaml").write_text("device_idx: 1\n")
    with pytest.raises(ConfigError, match="device_idx"):
        load_config(tmp_path)


def test_invalid_yaml_rejected(tmp_path: Path) -> None:
    (tmp_path / "system.yaml").write_text("log_level: [unclosed\n")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_local_override_wins_over_base(tmp_path: Path) -> None:
    (tmp_path / "camera.yaml").write_text("device_index: 0\nbackend: dshow\nfps: 30\n")
    local = tmp_path / "local"
    local.mkdir()
    (local / "camera.yaml").write_text("device_index: 2\nbackend: v4l2\n")
    cfg = load_config(tmp_path)
    assert cfg.camera.device_index == 2
    assert cfg.camera.backend == "v4l2"
    assert cfg.camera.fps == 30  # base value survives for keys not overridden


def test_local_override_merges_nested_sections(tmp_path: Path) -> None:
    (tmp_path / "robot.yaml").write_text(
        "pick_z: -42.0\nworkspace:\n  x_min: -10\n  x_max: 10\n"
    )
    local = tmp_path / "local"
    local.mkdir()
    (local / "robot.yaml").write_text("workspace:\n  x_max: 99\n")
    cfg = load_config(tmp_path)
    assert cfg.robot.pick_z == -42.0
    assert cfg.robot.workspace.x_min == -10
    assert cfg.robot.workspace.x_max == 99


def test_local_override_without_base_file(tmp_path: Path) -> None:
    local = tmp_path / "local"
    local.mkdir()
    (local / "vision.yaml").write_text("active_part: square_part\n")
    cfg = load_config(tmp_path)
    assert cfg.vision.active_part == "square_part"


def test_local_override_unknown_key_rejected(tmp_path: Path) -> None:
    local = tmp_path / "local"
    local.mkdir()
    (local / "camera.yaml").write_text("device_idx: 1\n")
    with pytest.raises(ConfigError, match="device_idx"):
        load_config(tmp_path)
