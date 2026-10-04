"""Milestone 11: end-to-end integration test without physical hardware.

Full chain: ReplayCamera -> ImageProcessor -> OpenCVDetector (synthetic
references) -> IdentityTransformer -> PickTargetManager (dedup lifecycle) ->
OpcUaRobotServer (request mode) <- asyncua client acting as the Delta robot.

Scene: two bright circles on dark background. The "robot" requests a target,
receives the nearest part, acknowledges the pick; the picked part is removed
from the scene (second replay image); the robot requests again and receives
the second part.
"""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from asyncua.sync import Client

from vision_system.app import VisionApplication
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

E2E_PORT = 48790
NAMESPACE = "http://camera-detection/vision"

BG, FG = 30, 220


def draw_scene(path: Path, circles: list[tuple[int, int, int]]) -> None:
    image = np.full((720, 1280, 3), BG, dtype=np.uint8)
    for cx, cy, r in circles:
        cv2.circle(image, (cx, cy), r, (FG, FG, FG), -1)
    cv2.imwrite(str(path), image)


@pytest.fixture
def e2e_config(tmp_path: Path) -> AppConfig:
    # reference dataset: one circle
    part_dir = tmp_path / "parts" / "round_part"
    part_dir.mkdir(parents=True)
    draw_scene(part_dir / "reference_01.jpg", [(640, 360, 90)])

    # replay scene: both frames show the same two parts (parts are stationary)
    replay_dir = tmp_path / "frames"
    replay_dir.mkdir()
    draw_scene(replay_dir / "frame_01.jpg", [(300, 300, 88), (900, 500, 92)])

    return AppConfig(
        camera=CameraConfig(type="replay", replay_dir=str(replay_dir)),
        vision=VisionConfig(
            active_part="round_part",
            parts_dir=str(tmp_path / "parts"),
            confidence_threshold=0.6,
            processing_mode="live",
        ),
        robot=RobotConfig(
            pick_z=-40.0,
            target_selection="nearest",
            dedup_radius_mm=15.0,
            picked_cooldown_s=60.0,  # parts never physically disappear in replay
            workspace=WorkspaceBounds(x_min=0, x_max=1280, y_min=0, y_max=720),
        ),
        communication=CommunicationConfig(
            interface="opcua",
            opcua=OpcUaConfig(
                endpoint=f"opc.tcp://127.0.0.1:{E2E_PORT}",
                namespace=NAMESPACE,
                mode="request",
            ),
        ),
        system=SystemConfig(
            web_enabled=False,
            calibration_file=str(tmp_path / "no_calibration.yaml"),  # Identity fallback
        ),
    )


def test_end_to_end_request_pick_cycle(e2e_config: AppConfig) -> None:
    app = VisionApplication(e2e_config)
    app.start()
    try:
        with Client(f"opc.tcp://127.0.0.1:{E2E_PORT}") as robot:
            idx = robot.get_namespace_index(NAMESPACE)
            node = lambda name: robot.nodes.objects.get_child(
                [f"{idx}:VisionSystem", f"{idx}:{name}"]
            )

            # no request yet: frames process, count published, no target offered
            app.process_one_frame()
            assert node("DetectedCount").read_value() == 2
            assert node("TargetReady").read_value() is False

            # robot requests -> nearest part (300, 300) published
            node("TargetRequest").write_value(True)
            deadline = time.time() + 3
            while node("TargetReady").read_value() is not True:
                app.process_one_frame()
                assert time.time() < deadline, "target was never published"
            assert node("TargetX").read_value() == pytest.approx(300, abs=3)
            assert node("TargetY").read_value() == pytest.approx(300, abs=3)
            assert node("TargetZ").read_value() == -40.0
            first_id = node("TargetId").read_value()

            # while pick in progress: more frames, no new target, same id
            for _ in range(3):
                app.process_one_frame()
            assert node("TargetId").read_value() == first_id

            # robot acknowledges; vision resets flags
            node("PickComplete").write_value(True)
            deadline = time.time() + 3
            while node("TargetReady").read_value() is not False:
                assert time.time() < deadline, "flags were not reset"
                time.sleep(0.05)

            # picked location is in cooldown: next request yields the OTHER part
            node("TargetRequest").write_value(True)
            deadline = time.time() + 3
            while node("TargetReady").read_value() is not True:
                app.process_one_frame()
                assert time.time() < deadline, "second target was never published"
            assert node("TargetX").read_value() == pytest.approx(900, abs=3)
            assert node("TargetY").read_value() == pytest.approx(500, abs=3)
            assert node("TargetId").read_value() == first_id + 1
    finally:
        app.stop()
