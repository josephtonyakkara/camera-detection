"""Curated hierarchical workflow definition for the /workflow page.

Three levels maximum. Each node: id, label, description, optional details
(file/function/inputs/outputs), optional live_states (cycle states that light
the block on level 1), optional children (sub-flow shown when drilled into).

Keep in sync with the actual pipeline (see AI_DEVELOPMENT_RULES.md doc table).
"""

from __future__ import annotations

from typing import Any

FLOW: dict[str, Any] = {
    "id": "main",
    "label": "Vision System Workflow (main.py)",
    "description": "Application lifecycle and the continuous frame pipeline",
    "children": [
        {
            "id": "start",
            "label": "Start",
            "description": "python main.py — composition root",
            "details": {
                "file": "main.py",
                "function": "main()",
                "inputs": "—",
                "outputs": "exit code",
            },
        },
        {
            "id": "load_config",
            "label": "Load configuration",
            "description": "5 YAML files, machine-local overrides merged over base",
            "details": {
                "file": "src/vision_system/config/loader.py",
                "function": "load_config()",
                "inputs": "config/*.yaml + config/local/*.yaml",
                "outputs": "AppConfig (typed dataclasses)",
            },
            "children": [
                {
                    "id": "read_base",
                    "label": "Read base files",
                    "description": "camera/vision/robot/communication/system.yaml (shared via git)",
                    "details": {
                        "file": "src/vision_system/config/loader.py",
                        "function": "_read_yaml()",
                        "inputs": "config/<name>.yaml",
                        "outputs": "dict per file",
                    },
                },
                {
                    "id": "merge_local",
                    "label": "Merge local overrides",
                    "description": "config/local/ wins per key, nested sections deep-merged",
                    "details": {
                        "file": "src/vision_system/config/loader.py",
                        "function": "deep_merge()",
                        "inputs": "base dict + local dict",
                        "outputs": "merged dict",
                    },
                },
                {
                    "id": "validate_config",
                    "label": "Validate",
                    "description": "unknown keys / wrong types rejected at startup",
                    "details": {
                        "file": "src/vision_system/config/loader.py",
                        "function": "_build() per model",
                        "inputs": "merged dict",
                        "outputs": "AppConfig or ConfigError",
                    },
                },
            ],
        },
        {
            "id": "logging",
            "label": "Logging setup",
            "description": "console + rotating file + web ring buffer",
            "details": {
                "file": "src/vision_system/utils/logging_setup.py",
                "function": "setup_logging()",
                "inputs": "level, log dir, LogBuffer",
                "outputs": "root logger handlers",
            },
        },
        {
            "id": "webapp",
            "label": "Web dashboard",
            "description": "FastAPI in a daemon thread; reads LiveState/AppControl contracts",
            "details": {
                "file": "src/webapp/server.py",
                "function": "start_web_server()",
                "inputs": "LiveState, AppControl, LogBuffer",
                "outputs": "6 pages + REST APIs on web_port",
            },
            "children": [
                {
                    "id": "live_page",
                    "label": "Live view",
                    "description": "MJPEG stream + status (LiveState snapshots)",
                },
                {
                    "id": "config_page",
                    "label": "Config editor",
                    "description": "edits config/local/, origin badges, restart workflow",
                },
                {
                    "id": "comm_page",
                    "label": "Communication",
                    "description": "OPC UA introspection: nodes, clients, handshake",
                },
                {
                    "id": "logs_page",
                    "label": "Logs",
                    "description": "live tail from the LogBuffer ring buffer",
                },
                {
                    "id": "state_page",
                    "label": "State machine",
                    "description": "pick-cycle states + transition history",
                },
            ],
        },
        {
            "id": "supervisor",
            "label": "Supervisor",
            "description": "runs the pipeline; rebuilds it with fresh config on restart",
            "details": {
                "file": "main.py",
                "function": "ApplicationSupervisor.run_forever()",
                "inputs": "restart requests (AppControl)",
                "outputs": "PipelineStatus",
            },
            "children": [
                {
                    "id": "build_app",
                    "label": "Build VisionApplication",
                    "description": "wire camera/detector/transformer/targets/robot from config",
                },
                {
                    "id": "run_loop",
                    "label": "Run frame loop",
                    "description": "process_one_frame() continuously (~30 fps)",
                },
                {
                    "id": "error_hold",
                    "label": "Error hold",
                    "description": "on failure: ERROR state, web stays alive, wait for restart",
                },
                {
                    "id": "rebuild",
                    "label": "Rebuild on restart",
                    "description": "teardown camera/robot, reload config, start again",
                },
            ],
        },
        {
            "id": "camera_capture",
            "label": "Camera capture",
            "description": "USB/replay driver behind CameraInterface",
            "live_states": ["frame_captured"],
            "details": {
                "file": "src/vision_system/camera/manager.py",
                "function": "CameraManager.get_frame()",
                "inputs": "—",
                "outputs": "FrameData (BGR ndarray, frame_id, timestamp)",
            },
            "children": [
                {
                    "id": "backend_select",
                    "label": "Backend selection",
                    "description": "auto → DirectShow (Windows) / V4L2 (Linux)",
                    "details": {
                        "file": "src/vision_system/camera/usb_camera.py",
                        "function": "resolve_backend()",
                        "inputs": "camera.backend",
                        "outputs": "OpenCV capture constant",
                    },
                },
                {
                    "id": "open_device",
                    "label": "Open device",
                    "description": "set resolution/fps; retry per reconnect policy",
                },
                {
                    "id": "warmup",
                    "label": "Warm-up frames",
                    "description": "discard first frames until auto-exposure settles",
                },
                {
                    "id": "get_frame",
                    "label": "Get frame",
                    "description": "latest image + one reconnect attempt on failure",
                },
            ],
        },
        {
            "id": "image_processing",
            "label": "Image processing",
            "description": "pre-processing stage (currently pass-through)",
            "details": {
                "file": "src/vision_system/processing/image_processor.py",
                "function": "ImageProcessor.process()",
                "inputs": "FrameData",
                "outputs": "ProcessedFrame",
            },
        },
        {
            "id": "part_detection",
            "label": "Part detection",
            "description": "reference-driven contour + shape matching",
            "live_states": ["parts_detected", "no_parts_found"],
            "details": {
                "file": "src/vision_system/detection/opencv_detector.py",
                "function": "OpenCVDetector.detect()",
                "inputs": "ProcessedFrame + ReferenceSet",
                "outputs": "DetectionResult (count + detections[])",
            },
            "children": [
                {
                    "id": "references",
                    "label": "Reference setup",
                    "description": "one-time at start: contours from parts/<active_part>/",
                    "children": [
                        {
                            "id": "ref_read",
                            "label": "Read images",
                            "description": "all images of the active part folder",
                        },
                        {
                            "id": "ref_contour",
                            "label": "Extract part contour",
                            "description": "largest fully-visible contour (border blobs excluded)",
                        },
                        {
                            "id": "ref_bounds",
                            "label": "Derive area bounds",
                            "description": "accepted size window from reference area fractions",
                        },
                    ],
                },
                {
                    "id": "grayscale",
                    "label": "Grayscale",
                    "description": "BGR → single channel",
                },
                {
                    "id": "blur",
                    "label": "Gaussian blur",
                    "description": "noise suppression (blur_kernel)",
                },
                {
                    "id": "threshold",
                    "label": "Threshold",
                    "description": "Otsu auto-split bright part vs dark background",
                },
                {
                    "id": "morphology",
                    "label": "Morphology",
                    "description": "open/close to clean the binary mask",
                },
                {
                    "id": "contours",
                    "label": "Find contours",
                    "description": "external contours = candidate parts",
                },
                {
                    "id": "area_filter",
                    "label": "Area filter",
                    "description": "min_area_px + reference-derived size window",
                },
                {
                    "id": "shape_match",
                    "label": "Shape match",
                    "description": "Hu-moment comparison against every reference contour",
                    "children": [
                        {
                            "id": "hu_moments",
                            "label": "Hu moments",
                            "description": "scale/rotation-invariant shape descriptors",
                        },
                        {
                            "id": "match_distance",
                            "label": "Match distance",
                            "description": "cv2.matchShapes, best over all references",
                        },
                        {
                            "id": "confidence",
                            "label": "Confidence",
                            "description": "1 / (1 + match_scale · distance), threshold gate",
                        },
                    ],
                },
                {
                    "id": "bounding_box",
                    "label": "Centroid + box",
                    "description": "sub-pixel centroid (moments) and bounding box per part",
                },
            ],
        },
        {
            "id": "coordinate_transform",
            "label": "Coordinate transformation",
            "description": "pixels → robot millimetres via homography",
            "live_states": ["coordinates_transformed"],
            "details": {
                "file": "src/vision_system/coordinates/transformer.py",
                "function": "HomographyTransformer.image_to_robot()",
                "inputs": "center_x_px, center_y_px",
                "outputs": "RobotCoordinate (x, y mm + pick_z)",
            },
            "children": [
                {
                    "id": "calib_load",
                    "label": "Load calibration",
                    "description": "homography.yaml at startup; Identity fallback (dev only)",
                },
                {
                    "id": "homography",
                    "label": "Homography multiply",
                    "description": "H · (x, y, 1) then perspective normalize",
                },
                {
                    "id": "pick_z",
                    "label": "Apply pick Z",
                    "description": "constant pick height from robot.yaml",
                },
            ],
        },
        {
            "id": "target_selection",
            "label": "Target selection",
            "description": "dedup lifecycle + strategy; one target in flight",
            "live_states": ["cooldown"],
            "details": {
                "file": "src/vision_system/targets/pick_target_manager.py",
                "function": "PickTargetManager.select_next()",
                "inputs": "DetectionResult",
                "outputs": "PickTarget or None",
            },
            "children": [
                {
                    "id": "workspace_check",
                    "label": "Workspace bounds",
                    "description": "targets outside robot.workspace are rejected",
                },
                {
                    "id": "dedup",
                    "label": "Duplicate suppression",
                    "description": "same physical part offered exactly once",
                    "children": [
                        {
                            "id": "in_progress",
                            "label": "In-progress check",
                            "description": "location of the dispatched target suppressed",
                        },
                        {
                            "id": "cooldown_check",
                            "label": "Cooldown check",
                            "description": "picked location suppressed for picked_cooldown_s",
                        },
                        {
                            "id": "reoffer",
                            "label": "Failed-pick re-offer",
                            "description": "part still present after cooldown → warning + re-offer",
                        },
                    ],
                },
                {
                    "id": "strategy",
                    "label": "Strategy sort",
                    "description": "nearest / leftmost / rightmost / highest confidence",
                },
                {
                    "id": "dispatch",
                    "label": "Dispatch",
                    "description": "assign target id, mark in-progress",
                },
            ],
        },
        {
            "id": "robot_comm",
            "label": "Robot communication",
            "description": "OPC UA server; robot is the polling client",
            "live_states": [
                "waiting_for_request",
                "request_received",
                "target_published",
                "picking",
                "pick_complete",
            ],
            "details": {
                "file": "src/vision_system/communication/opcua_server.py",
                "function": "OpcUaRobotServer",
                "inputs": "PickTarget",
                "outputs": "OPC UA nodes (Objects/VisionSystem)",
            },
            "children": [
                {
                    "id": "wait_request",
                    "label": "Wait for TargetRequest",
                    "description": "request mode: robot sets the request bit",
                },
                {
                    "id": "publish_target",
                    "label": "Publish target",
                    "description": "TargetX/Y/Z + TargetId written, TargetReady=True",
                },
                {
                    "id": "robot_pick",
                    "label": "Robot picks",
                    "description": "vision BUSY; no further targets offered",
                },
                {
                    "id": "ack",
                    "label": "PickComplete",
                    "description": "robot acknowledges; flags reset; cooldown starts",
                },
            ],
        },
    ],
}
