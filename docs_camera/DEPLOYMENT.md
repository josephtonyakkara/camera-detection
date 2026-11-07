# Deployment

How to get the system running on a new machine (Windows, Ubuntu/Debian, or
Raspberry Pi OS 64-bit). The same repository runs unchanged on all three; all
machine-specific state lives outside git.

## Quick Start on a New Machine

```bash
# Linux / Raspberry Pi
git clone <repo-url> camera-detection
cd camera-detection
bash scripts/setup.sh
.venv/bin/python main.py
```

```powershell
# Windows
git clone <repo-url> camera-detection
cd camera-detection
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
.venv\Scripts\python.exe main.py
```

The setup scripts check Python ≥ 3.11, create `.venv`, install the pinned
dependencies from `requirements.lock`, create `config/local/` and `logs/`, and
verify the imports. They are idempotent — safe to re-run.

## Dependency Files

| File | Purpose |
|---|---|
| `requirements.txt` | Ranged requirements (what the project needs) |
| `requirements.lock` | Exact pinned versions, identical on every machine — this is what the setup scripts install |

To upgrade a dependency: adjust `requirements.txt`, `pip install -r
requirements.txt --upgrade`, run the test suite, then regenerate the lock with
`pip freeze > requirements.lock` (restore the header comment).

## Per-Machine Configuration (`config/local/`)

The committed `config/*.yaml` files are portable defaults. Anything specific
to one machine goes in `config/local/<name>.yaml` (gitignored); the loader
merges local files over the base per key, nested sections included.

Typical `config/local/camera.yaml` after probing devices:

```yaml
device_index: 1   # from scripts/camera_check.py --list
```

Typical `config/local/system.yaml` on Windows (port 8000 can be reserved,
see TROUBLESHOOTING.md):

```yaml
web_port: 8080
```

The web config editor (`/config`) always writes to `config/local/`, so edits
made through the UI never dirty the git tree.

## Per-Machine Calibration

`calibration/homography.yaml` is camera-mount-specific and gitignored. On a
new machine/mount, run the calibration procedure (see COORDINATE_SYSTEM.md):

```bash
.venv/bin/python scripts/calibrate.py          # click-UI with live camera
```

Until a calibration exists, the app starts with an identity transform and
logs a warning — detection and the web UI work, but robot coordinates are
not meaningful.

## New-Machine Checklist

1. Clone + run the setup script for your OS.
2. `pytest -m "not hardware"` — must be green.
3. `python scripts/camera_check.py --list` — find the device index; put it in
   `config/local/camera.yaml`.
4. Run `scripts/calibrate.py` for the new camera mount.
5. `python main.py` — web UI at `http://<host>:8080`, OPC UA at port 5000.
6. Verify reachability from the LAN (see firewall notes below).

## OS-Specific Notes

### Raspberry Pi / Linux

- Needs Python ≥ 3.11 (Raspberry Pi OS Bookworm ships 3.11). If `python3` is
  older, install a newer one and run `PYTHON=python3.11 bash scripts/setup.sh`.
- `venv` module missing: `sudo apt install python3-venv`.
- OpenCV import error about `libGL.so.1`: `sudo apt install libgl1 libglib2.0-0`.
- Camera permission denied on `/dev/video*`: add the user to the `video`
  group (`sudo usermod -aG video $USER`, then re-login).
- Camera indices come from `/dev/video0`, `/dev/video1`, …; many UVC cameras
  expose two nodes per device — probe with `scripts/camera_check.py --list`.
- The `backend: auto` default resolves to V4L2 automatically.
- Firewall (if `ufw` active): `sudo ufw allow 8080/tcp` (web) and
  `sudo ufw allow 5000/tcp` (OPC UA).

### Windows

- `backend: auto` resolves to DirectShow (MSMF can hang opening external UVC
  cameras — see TROUBLESHOOTING.md).
- Port 8000 may fall in the Windows reserved port range (winerror 10013);
  the default `web_port` is 8080 for this reason.
- Windows re-enumerates USB cameras — re-probe the device index after
  re-plugging.

## What Stays Out of Git

| Path | Why |
|---|---|
| `config/local/` | per-machine config overrides |
| `calibration/homography.yaml` | per-camera-mount calibration |
| `logs/`, `*.yaml.bak`, `*.yaml.tmp` | runtime artifacts |
| `.venv/` | per-machine interpreter + packages |
