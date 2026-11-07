"""Tests for the workflow definition integrity and API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vision_system.models.cycle_state import CycleState
from webapp.flow_definition import FLOW
from webapp.routers.flow import make_flow_router


def walk(node: dict, depth: int = 0):
    yield node, depth
    for child in node.get("children", []):
        yield from walk(child, depth + 1)


def test_flow_ids_unique() -> None:
    ids = [n["id"] for n, _ in walk(FLOW)]
    assert len(ids) == len(set(ids)), "duplicate node ids in flow definition"


def test_flow_depth_max_three_levels_below_root() -> None:
    assert max(depth for _, depth in walk(FLOW)) <= 3


def test_flow_required_fields() -> None:
    for node, _ in walk(FLOW):
        assert node.get("id"), "node without id"
        assert node.get("label"), f"node {node['id']} without label"


def test_flow_live_states_are_valid_cycle_states() -> None:
    valid = {s.value for s in CycleState}
    for node, _ in walk(FLOW):
        for state in node.get("live_states", []):
            assert state in valid, f"{node['id']}: unknown cycle state {state!r}"


def test_flow_details_shape() -> None:
    for node, _ in walk(FLOW):
        details = node.get("details")
        if details:
            assert set(details) <= {"file", "function", "inputs", "outputs"}


def test_pipeline_cycle_states_all_mapped() -> None:
    # every pipeline-relevant cycle state should light some top-level block
    mapped = {s for n in FLOW["children"] for s in n.get("live_states", [])}
    expected = {
        "frame_captured", "parts_detected", "no_parts_found", "coordinates_transformed",
        "target_published", "picking", "pick_complete", "cooldown",
        "waiting_for_request", "request_received",
    }
    assert expected <= mapped


def test_flow_api() -> None:
    app = FastAPI()
    app.include_router(make_flow_router())
    payload = TestClient(app).get("/api/flow").json()
    assert payload["id"] == "main"
    assert any(c["id"] == "part_detection" for c in payload["children"])
