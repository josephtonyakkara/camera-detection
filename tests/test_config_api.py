"""Tests for the config editor API and the AppControl contract wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vision_system.app_control import AppControl, PipelineState, PipelineStatus
from webapp.routers.config_editor import make_config_router, make_system_router


class FakeControl(AppControl):
    def __init__(self) -> None:
        self.restart_required = False
        self.restart_requests = 0

    def get_status(self) -> PipelineStatus:
        return PipelineStatus(
            state=PipelineState.RUNNING, restart_required=self.restart_required
        )

    def mark_restart_required(self) -> None:
        self.restart_required = True

    def request_restart(self) -> None:
        self.restart_requests += 1


@pytest.fixture
def control() -> FakeControl:
    return FakeControl()


@pytest.fixture
def client(tmp_path: Path, control: FakeControl) -> TestClient:
    (tmp_path / "vision.yaml").write_text("active_part: round_part\n", encoding="utf-8")
    app = FastAPI()
    app.include_router(make_config_router(control, config_dir=tmp_path))
    app.include_router(make_system_router(control))
    return TestClient(app)


def test_get_all_returns_five_files(client: TestClient) -> None:
    payload = client.get("/api/config").json()
    assert set(payload) == {"camera", "vision", "robot", "communication", "system"}
    assert payload["vision"]["values"]["active_part"] == "round_part"
    assert payload["camera"]["raw"] == ""  # missing file -> defaults apply


def test_schema_contains_fields_and_nested_sections(client: TestClient) -> None:
    schema = client.get("/api/config/schema").json()
    camera_fields = {f["name"] for f in schema["camera"][""]}
    assert {"type", "device_index", "backend", "fps"} <= camera_fields
    assert "workspace" in schema["robot"]
    assert "opcua" in schema["communication"]
    vision_part = next(f for f in schema["vision"][""] if f["name"] == "active_part")
    assert vision_part["current"] == "round_part"


def test_save_raw_valid(client: TestClient, control: FakeControl, tmp_path: Path) -> None:
    response = client.post(
        "/api/config/vision", json={"raw": "active_part: braket_part\n"}
    )
    assert response.json() == {"saved": True, "restart_required": True}
    assert control.restart_required
    assert "braket_part" in (tmp_path / "vision.yaml").read_text()
    assert (tmp_path / "vision.yaml.bak").exists()  # previous content backed up


def test_save_values_valid(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/config/robot", json={"values": {"pick_z": -33.0, "workspace": {"x_min": -5}}}
    )
    assert response.status_code == 200
    assert "pick_z" in (tmp_path / "robot.yaml").read_text()


def test_save_unknown_key_rejected(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/config/camera", json={"raw": "device_idx: 1\n"})
    assert response.status_code == 400
    assert "device_idx" in response.json()["detail"]
    assert not (tmp_path / "camera.yaml").exists()  # file untouched


def test_save_invalid_yaml_rejected(client: TestClient) -> None:
    response = client.post("/api/config/system", json={"raw": "log_level: [unclosed\n"})
    assert response.status_code == 400
    assert "Invalid YAML" in response.json()["detail"]


def test_save_unknown_file_rejected(client: TestClient) -> None:
    assert client.post("/api/config/secrets", json={"raw": "a: 1"}).status_code == 404


def test_save_without_body_fields_rejected(client: TestClient) -> None:
    assert client.post("/api/config/vision", json={}).status_code == 422


def test_system_status_and_restart(client: TestClient, control: FakeControl) -> None:
    status = client.get("/api/system").json()
    assert status["state"] == "running"
    assert status["restart_required"] is False

    client.post("/api/config/vision", json={"raw": "active_part: round_part\n"})
    assert client.get("/api/system").json()["restart_required"] is True

    assert client.post("/api/system/restart").json() == {"restarting": True}
    assert control.restart_requests == 1


def test_vision_system_never_imports_webapp() -> None:
    """Architecture guarantee: the pipeline must run without the webapp package."""
    import re

    src = Path(__file__).resolve().parents[1] / "src" / "vision_system"
    pattern = re.compile(r"^\s*(import webapp|from webapp)", re.MULTILINE)
    offenders = [
        p for p in src.rglob("*.py") if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"vision_system must not import webapp: {offenders}"
