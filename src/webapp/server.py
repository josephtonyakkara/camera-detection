"""FastAPI application factory and server thread for the web frontend."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from vision_system.app_control import AppControl
from vision_system.config.models import SystemConfig
from vision_system.models.live_state import LiveState
from webapp.routers.communication import make_communication_router
from webapp.routers.config_editor import make_config_router, make_system_router
from webapp.routers.live import make_live_router

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _page(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def create_app(state: LiveState, control: AppControl | None = None) -> FastAPI:
    """Build the FastAPI app; control may be None for view-only deployments."""
    app = FastAPI(title="Vision System Dashboard")
    app.include_router(make_live_router(state))
    if control is not None:
        app.include_router(make_config_router(control))
        app.include_router(make_system_router(control))
        app.include_router(make_communication_router(control))

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _page("index.html")

    @app.get("/config", response_class=HTMLResponse)
    def config_page() -> str:
        return _page("config.html")

    @app.get("/communication", response_class=HTMLResponse)
    def communication_page() -> str:
        return _page("communication.html")

    return app


def start_web_server(
    state: LiveState, config: SystemConfig, control: AppControl | None = None
) -> threading.Thread:
    """Run uvicorn in a daemon thread; returns the thread."""
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(state, control),
            host=config.web_host,
            port=config.web_port,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, name="web-server", daemon=True)
    thread.start()
    logger.info("Web dashboard at http://%s:%d/", config.web_host, config.web_port)
    return thread
