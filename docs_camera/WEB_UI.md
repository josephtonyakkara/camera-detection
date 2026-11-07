# Web UI Reference

The web dashboard is served by the standalone `src/webapp/` package (FastAPI,
uvicorn daemon thread). Default address: `http://<host>:8080/`
(`system.web_host` / `system.web_port`). It communicates with the vision
application exclusively through the neutral contracts `LiveState` and
`AppControl` (see ARCHITECTURE.md).

## Pages

| Page | Path | Purpose |
|---|---|---|
| Live | `/` | annotated MJPEG stream, part count, robot state, in-flight pick target, FPS, candidate targets table |
| Configuration | `/config` | edit all 5 config files; save \u2192 restart workflow |
| Communication | `/communication` | OPC UA connection details, node catalog with live values, connected clients, handshake monitor || Logs | `/logs` | live color-coded log tail; level + module filters, pause, auto-scroll |
| State | `/statemachine` | pick-cycle state diagram with the current state lit + transition history with durations |
| Workflow | `/workflow` | drill-down flowchart of the whole system (3 levels, details per block, live stage highlighting) |
## Configuration page

- **Per-machine model**: saves always go to `config/local/<file>.yaml`
  (created on demand, gitignored). Base files are never modified by the UI.
- **Origin badges** per field: `default` (no file sets it), `base`
  (config/*.yaml, shared via git), `local` (this machine's override — wins).
- **Form view** submits only *changed* fields, so untouched values never
  become overrides. The `×` button next to a `local` badge removes that
  override (base/default applies again).
- **Raw YAML tab** edits the local override file directly; the base file is
  shown read-only underneath.
- Every change sets the restart-required flag; the **Restart pipeline**
  button rebuilds the application with freshly merged config. The restart
  button is also enabled in ERROR state for recovery.

## Communication page

- Connection card: bind endpoint, **connectable URLs per network interface**
  (copy buttons), namespace + index, security (None/Anonymous), mode, uptime.
- Handshake monitor: TargetRequest → TargetReady → PickComplete steps light
  up live, with StatusCode, current target, detected count.
- Node table: browse name, actual NodeId, type, writing side, live value.
- Connected clients: transport-level peer addresses. All data comes from the
  running OPC UA server, so config changes are reflected after restart.

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/status` | GET | live pipeline snapshot (LiveState) |
| `/stream` | GET | MJPEG stream (15 fps) |
| `/api/config` | GET | all files: base_raw, local_raw, merged values |
| `/api/config/schema` | GET | fields with type, default, current, origin |
| `/api/config/{file}` | POST | save raw YAML or changed values to config/local/ |
| `/api/config/{file}/override?key&section` | DELETE | remove one local override |
| `/api/system` | GET | pipeline state + restart-required flag |
| `/api/system/restart` | POST | rebuild pipeline with fresh config |
| `/api/communication` | GET | OPC UA introspection (CommunicationInfo) |
| `/api/logs?since&level&module` | GET | incremental log records from the ring buffer |
| `/api/cycle` | GET | pick-cycle state + transition history |
| `/api/flow` | GET | curated workflow hierarchy for the /workflow page |
