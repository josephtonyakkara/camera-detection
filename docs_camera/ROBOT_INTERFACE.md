# Robot Interface

## Isolation Principle

```
Vision pipeline → PickTarget → RobotInterface (abstraction) → robot controller → Delta robot
```

Vision code never talks to a protocol directly. The detector does not know
OPC UA exists; the robot interface does not know how images were processed.

## Interface Contract (`robot/base.py`)

| Method | Purpose |
|---|---|
| `connect()` | establish communication / start server |
| `send_pick_target(PickTarget)` | deliver a target; raises `RobotError` on failure — never silently pretends success |
| `get_robot_status()` | explicit `RobotStatus` (DISCONNECTED / CONNECTED / READY / BUSY / ERROR) |
| `is_robot_ready()` | gate: targets are only sent when True |
| `disconnect()` | idempotent shutdown |

## Implementations

| Class | Status | Purpose |
|---|---|---|
| `MockRobot` | done | dev/tests; records targets, READY when connected |
| `OpcUaRobotServer` | done (M10) | vision board runs the **OPC UA server**; robot controller is the client/master polling for targets |

Selected via `communication.interface` config (`mock` / `opcua`). Implementations
live in `communication/`; a future protocol (e.g. Modbus) is one new module
there plus a factory entry in `app.py:create_robot()`. All protocol parameters
live in `config/communication.yaml` — nothing is hardcoded.

## OPC UA Node Design (implemented)

Constraints from the robot controller: client supports only
Boolean/Int/Real types (no String), NoSecurity policy, and requires the
compatibility writes to `NodeId(2735)` (UInt16=10) and `NodeId(2267)`
(Byte=255) — both applied at server start.

Endpoint: `opc.tcp://0.0.0.0:5000` (config `communication.opcua.endpoint`).

```
Objects/VisionSystem/
├── TargetX          Double  (mm)  ─ written by vision
├── TargetY          Double  (mm)  ─ written by vision
├── TargetZ          Double  (mm)  ─ written by vision
├── TargetId         Int32         ─ written by vision
├── TargetRequest    Boolean       ─ robot sets True to request a target (request mode)
├── TargetReady      Boolean       ─ vision sets True when a new target is valid
├── PickComplete     Boolean       ─ robot sets True after picking (vision resets)
├── DetectedCount    Int32         ─ live part count (written on change)
└── StatusCode       Int32         ─ 0=starting, 1=ready, 2=target_ready
```

Handshake in `request` mode (default deployment):

```
robot:  TargetRequest=True                  (asks for a target)
vision: TargetX/Y/Z + TargetId, TargetReady=True, TargetRequest=False, StatusCode=2
robot:  reads target, picks                 → PickComplete=True
vision: resets PickComplete + TargetReady, StatusCode=1
        waits for the next TargetRequest
```

Handshake in `push` mode: identical, except vision publishes a new target as
soon as the previous one is acknowledged — `TargetRequest` is ignored.

While a target is pending, `send_pick_target()` raises `RobotError` and the
application withholds further targets. In request mode the same applies until
the robot sets `TargetRequest`. All variables are writable so the robot
client can set `TargetRequest`/`PickComplete`.

Threading: the asyncua server runs in a dedicated daemon thread with its own
asyncio loop (100 ms handshake poll); synchronous `RobotInterface` calls
bridge via `run_coroutine_threadsafe`.

## Introspection

`OpcUaRobotServer.get_communication_info()` returns a `CommunicationInfo`
snapshot (endpoint, connectable URLs per network interface, namespace+index,
mode, uptime, node catalog with live values, connected clients at transport
level). It is exposed to frontends through `AppControl` and shown on the
`/communication` dashboard page — everything an OPC UA client needs to
connect is visible there, including the live handshake state.

## Error Behaviour

- Robot not ready → target withheld, WARNING logged, retried on a later frame.
- Send failure → `RobotError` logged as ERROR; communication state remains explicit.
- Vision never assumes a pick happened without the robot's acknowledgement.
