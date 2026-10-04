"""Entry point: python main.py

Composition root: the only place where vision_system and webapp meet.
The supervisor owns the pipeline lifecycle and implements the AppControl
contract so the webapp can request restarts after config changes.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from vision_system.app import VisionApplication
from vision_system.app_control import AppControl, PipelineState, PipelineStatus
from vision_system.config.loader import load_config
from vision_system.models.live_state import LiveState
from vision_system.utils.logging_setup import setup_logging
from vision_system.utils.paths import resolve
from webapp import start_web_server

logger = logging.getLogger(__name__)

_RETRY_WAIT_S = 1.0


class ApplicationSupervisor(AppControl):
    """Runs the vision pipeline and rebuilds it with fresh config on request.

    On pipeline errors (e.g. camera unplugged) the supervisor keeps the web
    server alive in ERROR state and waits for a restart request instead of
    exiting, so configuration can still be fixed from the browser.
    """

    def __init__(self, live_state: LiveState | None) -> None:
        self._live_state = live_state
        self._lock = threading.Lock()
        self._status = PipelineStatus(state=PipelineState.STOPPED)
        self._restart_event = threading.Event()
        self._shutdown = False
        self._app: VisionApplication | None = None

    # ---- AppControl (called from the web thread) ----

    def get_status(self) -> PipelineStatus:
        with self._lock:
            return PipelineStatus(**vars(self._status))

    def mark_restart_required(self) -> None:
        with self._lock:
            self._status.restart_required = True

    def request_restart(self) -> None:
        logger.info("Restart requested")
        self._restart_event.set()
        app = self._app
        if app is not None:
            app.request_stop()

    def get_communication_info(self):
        app = self._app
        return app.get_communication_info() if app is not None else None

    # ---- lifecycle (main thread) ----

    def _set_state(self, state: PipelineState, message: str = "") -> None:
        with self._lock:
            self._status.state = state
            self._status.message = message
            if state is PipelineState.RUNNING:
                self._status.started_at = time.time()
                self._status.restart_required = False

    def run_forever(self) -> None:
        while not self._shutdown:
            self._restart_event.clear()
            self._set_state(PipelineState.STARTING)
            try:
                config = load_config()
                app = VisionApplication(config, live_state=self._live_state)
                self._app = app
                self._set_state(PipelineState.RUNNING)
                app.run()
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                self._shutdown = True
            except Exception as exc:
                logger.exception("Pipeline failed")
                self._set_state(PipelineState.ERROR, str(exc))
                # stay alive so the webapp can fix config and restart
                while not self._restart_event.wait(timeout=_RETRY_WAIT_S):
                    if self._shutdown:
                        return
                continue
            finally:
                self._app = None
            if not self._restart_event.is_set():
                break  # clean stop without restart request
            logger.info("Restarting pipeline with fresh configuration")
        self._set_state(PipelineState.STOPPED)


def main() -> int:
    config = load_config()
    setup_logging(config.system.log_level, resolve(config.system.log_dir))
    live_state = LiveState() if config.system.web_enabled else None
    supervisor = ApplicationSupervisor(live_state)
    if live_state is not None:
        start_web_server(live_state, config.system, control=supervisor)
    try:
        supervisor.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.exception("Fatal error")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
