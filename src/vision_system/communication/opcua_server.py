"""OPC UA server robot interface (Milestone 10).

The vision board acts as the OPC UA *server*; the Delta robot controller is
the client/master that polls pick targets and acknowledges picks.

Built on the pattern validated against the user's robot client:
NoSecurity policy, plain endpoint without URL path, writable variables with
explicit ua.Variant types, and the compatibility writes to NodeId 2735/2267
that the client requires. The robot supports only Boolean/Int/Real types, so
status is exposed as an Int32 code instead of a String.

Node layout (namespace from communication.opcua.namespace):

    Objects/VisionSystem/
        TargetX        Double   mm, written by vision
        TargetY        Double   mm, written by vision
        TargetZ        Double   mm, written by vision
        TargetId       Int32    written by vision
        TargetRequest  Boolean  robot sets True to request a target (request mode)
        TargetReady    Boolean  vision sets True when a new target is valid
        PickComplete   Boolean  robot sets True after picking; vision resets both
        DetectedCount  Int32    live part count
        StatusCode     Int32    0=starting, 1=ready, 2=target_ready

Handshake (mode=request, default deployment):
    robot writes TargetRequest=True -> vision publishes coordinates and sets
    TargetReady=True (resetting TargetRequest) -> robot reads XYZ, picks,
    writes PickComplete=True -> vision resets flags, ready for next request.
Handshake (mode=push):
    vision publishes a target whenever the previous one was acknowledged;
    TargetRequest is ignored.

The asyncua server runs in a dedicated daemon thread with its own asyncio
event loop; the synchronous RobotInterface methods bridge into it via
run_coroutine_threadsafe. All tunables come from config/communication.yaml.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import threading
import time
from typing import Any

from asyncua import Server, ua
from asyncua.crypto.security_policies import SecurityPolicyType

from vision_system.app_control import ClientInfo, CommunicationInfo, NodeInfo
from vision_system.communication.base import RobotError, RobotInterface
from vision_system.config.models import OpcUaConfig
from vision_system.models.data import PickTarget, RobotState, RobotStatus

logger = logging.getLogger(__name__)

STATUS_STARTING = 0
STATUS_READY = 1
STATUS_TARGET_READY = 2

# node -> (OPC UA type, which side writes it)
_NODE_META: dict[str, tuple[str, str]] = {
    "TargetX": ("Double", "vision"),
    "TargetY": ("Double", "vision"),
    "TargetZ": ("Double", "vision"),
    "TargetId": ("Int32", "vision"),
    "TargetRequest": ("Boolean", "robot"),
    "TargetReady": ("Boolean", "vision"),
    "PickComplete": ("Boolean", "robot"),
    "DetectedCount": ("Int32", "vision"),
    "StatusCode": ("Int32", "vision"),
}


class OpcUaRobotServer(RobotInterface):
    """Exposes pick targets to the robot controller via an embedded OPC UA server."""

    def __init__(self, config: OpcUaConfig) -> None:
        if config.mode not in ("push", "request"):
            raise RobotError(f"Unknown OPC UA mode {config.mode!r}; expected push or request")
        self._config = config
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._nodes: dict[str, Any] = {}
        self._started = threading.Event()
        self._stop_event: asyncio.Event | None = None
        self._start_error: Exception | None = None
        # state mirrored for synchronous readers; guarded by _state_lock
        self._state_lock = threading.Lock()
        self._connected = False
        self._target_pending = False
        self._target_requested = False  # request mode: robot has asked for a target
        self._current_target_id: int | None = None
        self._last_completed_id: int | None = None
        self._last_count: int | None = None
        self._server: Server | None = None
        self._namespace_index: int | None = None
        self._started_at: float | None = None

    # ---- RobotInterface (synchronous, called from the pipeline thread) ----

    def connect(self) -> None:
        if self._connected:
            return
        self._started.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._run_loop, name="opcua-server", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=self._config.start_timeout_s):
            raise RobotError("OPC UA server did not start in time")
        if self._start_error is not None:
            raise RobotError(f"OPC UA server failed to start: {self._start_error}")
        with self._state_lock:
            self._connected = True
        logger.info(
            "OPC UA server started at %s (mode=%s)", self._config.endpoint, self._config.mode
        )

    def send_pick_target(self, target: PickTarget) -> None:
        with self._state_lock:
            if not self._connected:
                raise RobotError("OPC UA server is not running")
            if self._target_pending:
                raise RobotError(
                    f"Robot busy: target {self._current_target_id} not yet acknowledged"
                )
            if self._config.mode == "request" and not self._target_requested:
                raise RobotError("Robot has not requested a target (TargetRequest is False)")
        self._run(self._publish_target(target))
        with self._state_lock:
            self._target_pending = True
            self._target_requested = False
            self._current_target_id = target.target_id
        logger.info(
            "Published target %d at (%.2f, %.2f, %.2f); TargetReady=True",
            target.target_id,
            target.coordinate.x,
            target.coordinate.y,
            target.coordinate.z,
        )

    def get_robot_status(self) -> RobotStatus:
        with self._state_lock:
            if not self._connected:
                return RobotStatus(state=RobotState.DISCONNECTED)
            state = RobotState.BUSY if self._target_pending else RobotState.READY
            return RobotStatus(state=state, last_pick_target_id=self._last_completed_id)

    def is_robot_ready(self) -> bool:
        with self._state_lock:
            if not self._connected or self._target_pending:
                return False
            if self._config.mode == "request":
                return self._target_requested
            return True

    def publish_detection_count(self, count: int) -> None:
        with self._state_lock:
            if not self._connected or count == self._last_count:
                return
            self._last_count = count
        self._run(
            self._nodes["DetectedCount"].write_value(ua.Variant(count, ua.VariantType.Int32))
        )

    def disconnect(self) -> None:
        with self._state_lock:
            if not self._connected:
                return
            self._connected = False
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("OPC UA server stopped")

    def get_communication_info(self) -> CommunicationInfo:
        """Introspection snapshot read from the live server (not the config)."""
        with self._state_lock:
            connected = self._connected
        info = CommunicationInfo(
            server_running=connected,
            interface="opcua",
            endpoint=self._config.endpoint,
            mode=self._config.mode,
            namespace=self._config.namespace,
            namespace_index=self._namespace_index,
            connect_urls=self._connect_urls(),
            uptime_s=(time.time() - self._started_at) if connected and self._started_at else None,
        )
        if not connected:
            return info
        try:
            info.nodes, info.clients = self._run(self._collect_info())
        except RobotError as exc:
            logger.warning("Communication introspection failed: %s", exc)
        return info

    def _connect_urls(self) -> list[str]:
        port = self._config.endpoint.rsplit(":", 1)[-1].strip("/")
        urls = [f"opc.tcp://localhost:{port}"]
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                urls.append(f"opc.tcp://{ip}:{port}")
        except OSError:  # hostname resolution unavailable; localhost still valid
            pass
        return urls

    async def _collect_info(self) -> tuple[list[NodeInfo], list[ClientInfo]]:
        nodes = []
        for name, node in self._nodes.items():
            data_type, writer = _NODE_META.get(name, ("?", "vision"))
            nodes.append(
                NodeInfo(
                    browse_name=name,
                    node_id=node.nodeid.to_string(),
                    data_type=data_type,
                    writable=True,
                    value=await node.read_value(),
                    writer=writer,
                )
            )
        clients = []
        # transport-level client view; asyncua keeps open transports on the internal server
        transports = getattr(getattr(self._server, "iserver", None), "asyncio_transports", [])
        for transport in transports:
            peer = transport.get_extra_info("peername")
            if peer:
                clients.append(ClientInfo(address=f"{peer[0]}:{peer[1]}"))
        return nodes, clients

    # ---- server thread ----

    def _run(self, coroutine) -> Any:
        """Execute a coroutine on the server loop from the caller thread."""
        if self._loop is None:
            raise RobotError("OPC UA server loop not running")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=self._config.call_timeout_s)
        except Exception as exc:
            raise RobotError(f"OPC UA operation failed: {exc}") from exc

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:  # startup failures surface via _start_error
            self._start_error = exc
            self._started.set()
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        self._stop_event = asyncio.Event()
        server = Server()
        await server.init()
        server.set_endpoint(self._config.endpoint)
        server.set_security_policy([SecurityPolicyType.NoSecurity])
        idx = await server.register_namespace(self._config.namespace)
        self._server = server
        self._namespace_index = idx

        vision = await server.get_objects_node().add_object(idx, "VisionSystem")
        # robot client supports only Boolean/Int/Real types (no String)
        spec = {
            "TargetX": ua.Variant(0.0, ua.VariantType.Double),
            "TargetY": ua.Variant(0.0, ua.VariantType.Double),
            "TargetZ": ua.Variant(0.0, ua.VariantType.Double),
            "TargetId": ua.Variant(0, ua.VariantType.Int32),
            "TargetRequest": ua.Variant(False, ua.VariantType.Boolean),
            "TargetReady": ua.Variant(False, ua.VariantType.Boolean),
            "PickComplete": ua.Variant(False, ua.VariantType.Boolean),
            "DetectedCount": ua.Variant(0, ua.VariantType.Int32),
            "StatusCode": ua.Variant(STATUS_STARTING, ua.VariantType.Int32),
        }
        for name, variant in spec.items():
            node = await vision.add_variable(idx, name, variant)
            await node.set_writable(True)  # robot client must write PickComplete
            self._nodes[name] = node

        # compatibility writes the robot's UA client requires (validated setup)
        for node_id, variant in (
            (2735, ua.Variant(10, ua.VariantType.UInt16)),
            (2267, ua.Variant(255, ua.VariantType.Byte)),
        ):
            try:
                await server.get_node(ua.NodeId(node_id)).write_value(variant)
            except Exception as exc:
                logger.debug("Compatibility write to NodeId(%d) skipped: %s", node_id, exc)

        async with server:
            await self._set_status(STATUS_READY)
            self._started_at = time.time()
            self._started.set()
            while not self._stop_event.is_set():
                await self._poll_handshake()
                if self._config.mode == "request":
                    await self._poll_request()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._config.handshake_poll_s
                    )
                except TimeoutError:
                    pass

    async def _set_status(self, code: int) -> None:
        await self._nodes["StatusCode"].write_value(ua.Variant(code, ua.VariantType.Int32))

    async def _publish_target(self, target: PickTarget) -> None:
        coord = target.coordinate
        await self._nodes["TargetX"].write_value(ua.Variant(float(coord.x), ua.VariantType.Double))
        await self._nodes["TargetY"].write_value(ua.Variant(float(coord.y), ua.VariantType.Double))
        await self._nodes["TargetZ"].write_value(ua.Variant(float(coord.z), ua.VariantType.Double))
        await self._nodes["TargetId"].write_value(
            ua.Variant(int(target.target_id), ua.VariantType.Int32)
        )
        await self._nodes["TargetReady"].write_value(ua.Variant(True, ua.VariantType.Boolean))
        await self._nodes["TargetRequest"].write_value(ua.Variant(False, ua.VariantType.Boolean))
        await self._set_status(STATUS_TARGET_READY)

    async def _poll_request(self) -> None:
        """Request mode: latch the robot's TargetRequest bit."""
        with self._state_lock:
            if self._target_pending or self._target_requested:
                return
        if not await self._nodes["TargetRequest"].read_value():
            return
        with self._state_lock:
            self._target_requested = True
        logger.info("Robot requested a target (TargetRequest=True)")

    async def _poll_handshake(self) -> None:
        with self._state_lock:
            pending = self._target_pending
        if not pending:
            return
        if not await self._nodes["PickComplete"].read_value():
            return
        await self._nodes["PickComplete"].write_value(ua.Variant(False, ua.VariantType.Boolean))
        await self._nodes["TargetReady"].write_value(ua.Variant(False, ua.VariantType.Boolean))
        await self._set_status(STATUS_READY)
        with self._state_lock:
            self._last_completed_id = self._current_target_id
            self._target_pending = False
        logger.info("Robot acknowledged pick of target %s", self._last_completed_id)
