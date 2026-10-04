"""Live view endpoints: MJPEG stream and pipeline status JSON."""

from __future__ import annotations

import time
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from vision_system.models.live_state import LiveState

_STREAM_FPS = 15.0


def _mjpeg_generator(state: LiveState) -> Iterator[bytes]:
    while True:
        jpeg = state.get_jpeg()
        if jpeg is not None:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        time.sleep(1.0 / _STREAM_FPS)


def make_live_router(state: LiveState) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    def status() -> dict:
        return state.get_status()

    @router.get("/stream")
    def stream() -> Response:
        return StreamingResponse(
            _mjpeg_generator(state),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    return router
