"""Pick-cycle state machine API."""

from __future__ import annotations

from fastapi import APIRouter

from vision_system.app_control import AppControl


def make_cycle_router(control: AppControl) -> APIRouter:
    router = APIRouter(prefix="/api/cycle")

    @router.get("")
    def cycle() -> dict:
        snapshot = control.get_cycle_snapshot()
        if snapshot is None:
            return {"state": "unavailable", "detail": "pipeline not running", "history": []}
        return snapshot

    return router
