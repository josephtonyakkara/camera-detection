"""Control contract between the application supervisor and external consumers.

The webapp (or any other frontend) depends only on this interface and the
dataclasses it returns — never on VisionApplication internals. Implemented by
the supervisor in main.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class PipelineState(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PipelineStatus:
    """Snapshot of the supervised application state."""

    state: PipelineState
    message: str = ""
    restart_required: bool = False
    started_at: float | None = None


@dataclass(frozen=True)
class NodeInfo:
    """One OPC UA node as exposed to clients."""

    browse_name: str
    node_id: str
    data_type: str
    writable: bool
    value: object
    writer: str  # "vision" or "robot"


@dataclass(frozen=True)
class ClientInfo:
    """One connected OPC UA client (transport level)."""

    address: str


@dataclass
class CommunicationInfo:
    """Snapshot of the robot-communication server for frontends."""

    server_running: bool
    interface: str
    endpoint: str
    mode: str = ""
    namespace: str = ""
    namespace_index: int | None = None
    security: str = "None (Anonymous)"
    connect_urls: list[str] = field(default_factory=list)
    uptime_s: float | None = None
    nodes: list[NodeInfo] = field(default_factory=list)
    clients: list[ClientInfo] = field(default_factory=list)


class AppControl(ABC):
    """Commands a frontend may issue toward the application supervisor."""

    @abstractmethod
    def get_status(self) -> PipelineStatus:
        """Current pipeline state including the restart-required flag."""

    @abstractmethod
    def mark_restart_required(self) -> None:
        """Flag that saved configuration changes need a restart to apply."""

    @abstractmethod
    def request_restart(self) -> None:
        """Ask the supervisor to tear down and rebuild the pipeline with fresh config."""

    def get_communication_info(self) -> CommunicationInfo | None:
        """Live robot-communication snapshot; None when unavailable."""
        return None
