"""Standalone web frontend package.

Depends only on the neutral contracts in vision_system (models.live_state,
app_control, config loader validation). vision_system never imports webapp;
the composition happens exclusively in main.py.
"""

from webapp.server import create_app, start_web_server

__all__ = ["create_app", "start_web_server"]
