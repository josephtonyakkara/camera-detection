"""Typed configuration models mirroring the YAML files in config/."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CameraConfig:
    """Mirrors config/camera.yaml."""

    type: str = "usb"
    device_index: int = 0
    backend: str = "auto"  # auto | dshow | msmf | v4l2
    replay_dir: str = ""   # image folder for type: replay (tests/dev without hardware)
    width: int = 1280
    height: int = 720
    fps: int = 30
    warmup_frames: int = 5  # frames discarded after open (auto-exposure settling)
    reconnect_attempts: int = 3
    reconnect_delay_s: float = 2.0


@dataclass
class VisionConfig:
    """Mirrors config/vision.yaml."""

    detector: str = "opencv"
    active_part: str = "round_part"
    parts_dir: str = "parts"
    confidence_threshold: float = 0.6
    processing_mode: str = "live"
    detection_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceBounds:
    """Robot workspace limits in robot coordinates (mm)."""

    x_min: float = -200.0
    x_max: float = 200.0
    y_min: float = -200.0
    y_max: float = 200.0

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


@dataclass
class RobotConfig:
    """Mirrors config/robot.yaml."""

    pick_z: float = -50.0
    target_selection: str = "nearest"
    dedup_radius_mm: float = 15.0  # detections within this radius are the same part
    picked_cooldown_s: float = 3.0  # suppress a picked location this long
    workspace: WorkspaceBounds = field(default_factory=WorkspaceBounds)


@dataclass
class OpcUaConfig:
    """OPC UA server settings (config/communication.yaml, opcua block)."""

    endpoint: str = "opc.tcp://0.0.0.0:5000"
    namespace: str = "http://camera-detection/vision"
    mode: str = "push"  # push = publish when robot idle; request = robot sets TargetRequest first
    handshake_poll_s: float = 0.1
    start_timeout_s: float = 15.0
    call_timeout_s: float = 5.0


@dataclass
class CommunicationConfig:
    """Mirrors config/communication.yaml."""

    interface: str = "mock"  # mock | opcua
    opcua: OpcUaConfig = field(default_factory=OpcUaConfig)


@dataclass
class SystemConfig:
    """Mirrors config/system.yaml."""

    log_level: str = "INFO"
    log_dir: str = "logs"
    calibration_file: str = "calibration/homography.yaml"
    web_enabled: bool = True
    web_host: str = "0.0.0.0"
    web_port: int = 8000


@dataclass
class AppConfig:
    """Aggregated application configuration."""

    camera: CameraConfig = field(default_factory=CameraConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    communication: CommunicationConfig = field(default_factory=CommunicationConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
