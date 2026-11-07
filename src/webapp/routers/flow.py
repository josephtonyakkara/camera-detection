"""Workflow definition API."""

from __future__ import annotations

from fastapi import APIRouter

from webapp.flow_definition import FLOW


def make_flow_router() -> APIRouter:
    router = APIRouter(prefix="/api/flow")

    @router.get("")
    def flow() -> dict:
        return FLOW

    return router
