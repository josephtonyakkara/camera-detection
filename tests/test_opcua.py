"""Integration tests for the OPC UA robot server.

Uses asyncua's synchronous client wrapper as a simulated robot controller on
localhost — no hardware and no pytest-asyncio needed.
"""

from __future__ import annotations

import time

import pytest
from asyncua.sync import Client

from vision_system.communication.base import RobotError
from vision_system.communication.opcua_server import (
    STATUS_READY,
    STATUS_TARGET_READY,
    OpcUaRobotServer,
)
from vision_system.config.models import OpcUaConfig
from vision_system.models.data import PickTarget, RobotCoordinate, RobotState

TEST_PORT = 48765  # avoid clashing with a real server on 5000


def make_config(port: int = TEST_PORT, mode: str = "push") -> OpcUaConfig:
    return OpcUaConfig(
        endpoint=f"opc.tcp://127.0.0.1:{port}",
        namespace="http://camera-detection/vision",
        mode=mode,
    )


@pytest.fixture
def server():
    robot = OpcUaRobotServer(make_config())
    robot.connect()
    yield robot
    robot.disconnect()


@pytest.fixture
def client(server):
    with Client(f"opc.tcp://127.0.0.1:{TEST_PORT}") as ua_client:
        idx = ua_client.get_namespace_index("http://camera-detection/vision")
        nodes = {
            name: ua_client.nodes.objects.get_child([f"{idx}:VisionSystem", f"{idx}:{name}"])
            for name in (
                "TargetX", "TargetY", "TargetZ", "TargetId", "TargetRequest",
                "TargetReady", "PickComplete", "DetectedCount", "StatusCode",
            )
        }
        yield nodes


def make_target(target_id: int = 1) -> PickTarget:
    return PickTarget(
        target_id=target_id,
        coordinate=RobotCoordinate(120.5, -35.25, -50.0),
        class_name="round_part",
        confidence=0.95,
        source_frame_id=7,
    )


def wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_server_starts_ready(server, client) -> None:
    assert server.is_robot_ready()
    assert server.get_robot_status().state is RobotState.READY
    assert client["StatusCode"].read_value() == STATUS_READY
    assert client["TargetReady"].read_value() is False


def test_target_published_with_correct_types(server, client) -> None:
    server.send_pick_target(make_target(42))
    assert client["TargetX"].read_value() == pytest.approx(120.5)
    assert client["TargetY"].read_value() == pytest.approx(-35.25)
    assert client["TargetZ"].read_value() == pytest.approx(-50.0)
    assert client["TargetId"].read_value() == 42
    assert client["TargetReady"].read_value() is True
    assert client["StatusCode"].read_value() == STATUS_TARGET_READY


def test_busy_until_robot_acknowledges(server, client) -> None:
    server.send_pick_target(make_target(1))
    assert not server.is_robot_ready()
    assert server.get_robot_status().state is RobotState.BUSY
    with pytest.raises(RobotError, match="busy"):
        server.send_pick_target(make_target(2))


def test_pick_complete_handshake(server, client) -> None:
    server.send_pick_target(make_target(7))
    client["PickComplete"].write_value(True)  # robot acknowledges

    assert wait_for(server.is_robot_ready), "server did not return to ready"
    status = server.get_robot_status()
    assert status.state is RobotState.READY
    assert status.last_pick_target_id == 7
    assert client["TargetReady"].read_value() is False
    assert client["PickComplete"].read_value() is False
    assert client["StatusCode"].read_value() == STATUS_READY

    server.send_pick_target(make_target(8))  # next target accepted
    assert client["TargetId"].read_value() == 8


def test_detection_count_published(server, client) -> None:
    server.publish_detection_count(5)
    assert client["DetectedCount"].read_value() == 5
    server.publish_detection_count(5)  # unchanged: no-op, still 5
    assert client["DetectedCount"].read_value() == 5


def test_send_when_disconnected_raises() -> None:
    robot = OpcUaRobotServer(make_config(TEST_PORT + 1))
    with pytest.raises(RobotError, match="not running"):
        robot.send_pick_target(make_target())


def test_invalid_mode_rejected() -> None:
    with pytest.raises(RobotError, match="Unknown OPC UA mode"):
        OpcUaRobotServer(make_config(mode="telepathy"))


def test_request_mode_full_cycle() -> None:
    robot = OpcUaRobotServer(make_config(TEST_PORT + 2, mode="request"))
    robot.connect()
    try:
        with Client(f"opc.tcp://127.0.0.1:{TEST_PORT + 2}") as ua_client:
            idx = ua_client.get_namespace_index("http://camera-detection/vision")
            node = lambda name: ua_client.nodes.objects.get_child(
                [f"{idx}:VisionSystem", f"{idx}:{name}"]
            )
            # not ready until the robot requests
            assert not robot.is_robot_ready()
            with pytest.raises(RobotError, match="not requested"):
                robot.send_pick_target(make_target(1))

            node("TargetRequest").write_value(True)  # robot asks for a target
            assert wait_for(robot.is_robot_ready), "request was not latched"

            robot.send_pick_target(make_target(5))
            assert node("TargetReady").read_value() is True
            assert node("TargetRequest").read_value() is False  # reset on publish
            assert node("TargetId").read_value() == 5
            assert not robot.is_robot_ready()  # pending + no new request

            node("PickComplete").write_value(True)  # robot picked
            assert wait_for(
                lambda: robot.get_robot_status().last_pick_target_id == 5
            ), "handshake did not complete"
            assert not robot.is_robot_ready()  # still needs a new request
    finally:
        robot.disconnect()


def test_disconnect_is_idempotent(server) -> None:
    server.disconnect()
    server.disconnect()
    assert server.get_robot_status().state is RobotState.DISCONNECTED


def test_communication_info_running(server, client) -> None:
    info = server.get_communication_info()
    assert info.server_running is True
    assert info.interface == "opcua"
    assert info.mode == "push"
    assert info.namespace_index == 2
    assert info.uptime_s is not None and info.uptime_s >= 0
    assert any(u.startswith("opc.tcp://localhost:") for u in info.connect_urls)
    names = {n.browse_name for n in info.nodes}
    assert names == {
        "TargetX", "TargetY", "TargetZ", "TargetId", "TargetRequest",
        "TargetReady", "PickComplete", "DetectedCount", "StatusCode",
    }
    target_x = next(n for n in info.nodes if n.browse_name == "TargetX")
    assert target_x.node_id.startswith("ns=2;")
    assert target_x.data_type == "Double"
    assert target_x.writer == "vision"
    # the test client fixture is connected and must appear at transport level
    assert any(c.address.startswith("127.0.0.1") for c in info.clients)


def test_communication_info_when_stopped() -> None:
    robot = OpcUaRobotServer(make_config(TEST_PORT + 3))
    info = robot.get_communication_info()
    assert info.server_running is False
    assert info.nodes == []
    assert info.clients == []
