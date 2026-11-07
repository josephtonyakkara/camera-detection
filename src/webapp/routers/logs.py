"""Live log tail API backed by the LogBuffer ring buffer."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from vision_system.models.log_buffer import LogBuffer


def make_logs_router(buffer: LogBuffer) -> APIRouter:
    router = APIRouter(prefix="/api/logs")

    @router.get("")
    def logs(since: int = 0, level: str = "DEBUG", module: str = "") -> dict:
        min_levelno = logging.getLevelName(level.upper())
        if not isinstance(min_levelno, int):
            min_levelno = logging.DEBUG
        return {
            "records": buffer.get_records(since=since, min_levelno=min_levelno, module=module),
            "last_seq": buffer.last_seq,
        }

    return router
