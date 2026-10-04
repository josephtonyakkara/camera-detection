"""Communication status API: live OPC UA server introspection via AppControl."""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter

from vision_system.app_control import AppControl


def make_communication_router(control: AppControl) -> APIRouter:
    router = APIRouter(prefix="/api/communication")

    @router.get("")
    def communication() -> dict:
        info = control.get_communication_info()
        if info is None:
            return {
                "server_running": False,
                "interface": "mock-or-stopped",
                "reason": "No OPC UA server active (interface is mock or pipeline not running)",
            }
        return dataclasses.asdict(info)

    return router
