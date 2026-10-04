# Milestones

Confirmed project decisions: USB webcam (RGB), classical OpenCV first (YOLO
later), multiple non-overlapping parts on a flat plane (center only), fixed
top-down camera with constant pick Z (planar homography), Python as OPC UA
server, FastAPI web UI, Windows dev / Linux deploy.

| # | Milestone | Deliverable | Status |
|---|---|---|---|
| 1 | Project architecture | Folder structure, data models, interfaces, config system, docs, test scaffold | **✅ Done** (2026-08-13) |
| 2 | Camera integration | Stable `CameraManager` + USB driver, reconnect handling, live smoke test | **✅ Done** (2026-08-19) — 4 hardware tests pass at 1280×720 BGR; sample frames verified via `scripts/camera_check.py` |
| 3 | Live video pipeline | Continuous loop, processing modes, debug visualization, basic web live view | **✅ Done** (2026-08-19) — live loop ~30 fps, debug window, FastAPI dashboard with MJPEG stream + status API |
| 4 | Part detection | OpenCV detection against reference images → populated `DetectionResult` | **✅ Done** (2026-09-05) — contour + Hu-moment matching; 23/23 references and live frame detected at conf ≥0.999 |
| 5 | Part counting | Reliable multi-object detection + count | **✅ Done** (2026-09-05) — 3 parts counted in 30/30 live frames (100% stable); edge-clipped part correctly reduced confidence |
| 6 | Reference dataset / dynamic part selection | Config-driven part switching validated end-to-end | **✅ Done** (2026-09-05) — round↔bracket switching via `active_part` only; cross-class rejection verified both directions |
| 7 | Camera calibration | Homography acquisition procedure + persisted calibration | **✅ Done** (2026-09-05 tooling, physical run performed; RMS 3.49 mm — re-calibration for accuracy planned) |
| 8 | Image-to-robot coordinates | Validated pixel→mm transformation accuracy | **✅ Done** (2026-10-03) — real-world pixel→robot conversion tested by user; accuracy optimization deferred to a future calibrate.py run |
| 9 | Pick target generation | Strategy selection, workspace bounds, no duplicate/invalid targets | **✅ Done** (2026-10-03) — cross-frame dedup by robot-space location, single target in flight, pick cooldown + failed-pick re-offer |
| 10 | Robot communication | asyncua OPC UA server, node handshake, mock-client tests | **✅ Done** (2026-09-05) — `communication/opcua_server.py`, port 5000, Int32/Double/Boolean nodes only, 7 client-integration tests incl. full pick handshake |
| 11 | End-to-end integration | Full camera→robot chain incl. web dashboard | 🔶 Software E2E done (2026-10-03): full chain validated in an automated test (replay camera → detection → dedup → OPC UA ← simulated robot client, request mode). OPC UA server also live-tested with UaExpert. Physical run with camera + robot pending |
| 12 | Validation & optimization | Accuracy/latency/repeatability measurements documented | ⬜ Not started |
| 13 | Web package separation + control channel | `src/webapp/` standalone package, AppControl contract, supervisor with web-triggered restart, config read/validate/save API | **✅ Done** (2026-10-03) |
| 14 | Web config editor page | Form + raw YAML tabs, save → restart-required banner → restart button | **✅ Done** (2026-10-03) — full cycle validated live: edit → save → banner → restart → pipeline rebuilt with fresh config |
| 15 | Communication introspection backend | `CommunicationInfo` via AppControl: endpoint URLs, nodes, clients, live values | **✅ Done** (2026-10-03) — live server introspection incl. transport-level client tracking |
| 16 | Communication dashboard page | Connection card, node table, clients, live handshake monitor | **✅ Done** (2026-10-03) — validated live: request-mode handshake visible, 2 clients tracked, copyable connect URLs per interface |

Legend: ✅ done · 🔶 partially done · ⬜ not started

## Next Steps

1. **M11 physical run**: reconnect the camera, set `communication.interface: opcua`,
   run `python main.py`, drive the cycle from the robot (or UaExpert as stand-in).
2. Re-run `scripts/calibrate.py` with more, wider-spread markers to improve the
   3.49 mm RMS (optimization deferred by user decision).
3. **M12**: accuracy/latency/repeatability measurement.
4. Recapture flagged reference images (round: 07/12/17, bracket: 04/06).

## Known Limitations (M4/M5)

- Parts touching other bright objects merge into one blob (seen in
  reference_07); keep the workspace background clear.
- Parts clipped by the frame edge get reduced confidence and may drop below
  the threshold; keep parts fully inside the camera view.
- Otsu thresholding assumes bright parts on a dark background; use
  `detection_params.invert: true` for the opposite case.
