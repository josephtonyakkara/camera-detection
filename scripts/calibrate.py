"""Milestone 7 camera-to-robot calibration tool.

Place >=4 markers at known robot XY positions in the camera view, then:

    python scripts/calibrate.py
        Live window opens. Left-click each marker (in order), press U to undo,
        ENTER when done. For every click you are asked for the robot X and Y
        (mm) in the console. Result is saved to system.calibration_file.

    python scripts/calibrate.py --from-file calibration/points.yaml
        Headless: reads point pairs from YAML:
            points:
              - {pixel: [852, 415], robot: [120.0, -35.5]}
              - ...

    python scripts/calibrate.py --verify
        Loads the saved calibration and reprojects its stored points.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cv2
import yaml

from vision_system.camera.manager import CameraManager
from vision_system.config.loader import load_config
from vision_system.coordinates.calibration import (
    CalibrationPoint,
    compute_homography,
    load_calibration,
    save_calibration,
)
from vision_system.utils.logging_setup import setup_logging
from vision_system.utils.paths import resolve

logger = logging.getLogger("calibrate")


def collect_points_interactive(config) -> list[CalibrationPoint]:
    clicks: list[tuple[int, int]] = []

    def on_mouse(event: int, x: int, y: int, flags: int, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            clicks.append((x, y))

    camera = CameraManager(config.camera)
    camera.start()
    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)
    logger.info("Click markers (>=4). U = undo last, ENTER = done, ESC = abort.")
    try:
        while True:
            frame = camera.get_frame()
            display = frame.image.copy()
            for i, (x, y) in enumerate(clicks, start=1):
                cv2.drawMarker(display, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
                cv2.putText(display, str(i), (x + 8, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, f"points: {len(clicks)}  (U undo, ENTER done, ESC abort)",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("calibrate", display)
            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                logger.info("Aborted")
                return []
            if key in (ord("u"), ord("U")) and clicks:
                clicks.pop()
            if key in (13, 10):
                if len(clicks) >= 4:
                    break
                logger.warning("Need at least 4 points, have %d", len(clicks))
    finally:
        camera.stop()
        cv2.destroyAllWindows()

    points: list[CalibrationPoint] = []
    for i, (x, y) in enumerate(clicks, start=1):
        print(f"Marker {i} at pixel ({x}, {y}):")
        robot_x = float(input("  robot X (mm): ").strip())
        robot_y = float(input("  robot Y (mm): ").strip())
        points.append(CalibrationPoint(x, y, robot_x, robot_y))
    return points


def load_points_file(path: Path) -> list[CalibrationPoint]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        CalibrationPoint(p["pixel"][0], p["pixel"][1], p["robot"][0], p["robot"][1])
        for p in data["points"]
    ]


def verify(calibration_file: Path) -> None:
    matrix = load_calibration(calibration_file)
    data = yaml.safe_load(calibration_file.read_text(encoding="utf-8"))
    logger.info("Calibration created %s, stored RMS %.3f mm", data["created"], data["rms_error_mm"])
    import numpy as np

    for p in data["points"]:
        vec = matrix @ np.array([p["pixel"][0], p["pixel"][1], 1.0])
        rx, ry = vec[0] / vec[2], vec[1] / vec[2]
        err = float(np.hypot(rx - p["robot"][0], ry - p["robot"][1]))
        logger.info(
            "pixel (%.0f, %.0f) -> (%.2f, %.2f) mm, expected (%.2f, %.2f), error %.3f mm",
            p["pixel"][0], p["pixel"][1], rx, ry, p["robot"][0], p["robot"][1], err,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-file", type=Path, metavar="YAML", help="read point pairs from file")
    parser.add_argument("--verify", action="store_true", help="reproject stored calibration points")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.system.log_level)
    calibration_file = resolve(config.system.calibration_file)

    if args.verify:
        verify(calibration_file)
        return 0

    points = (
        load_points_file(args.from_file) if args.from_file else collect_points_interactive(config)
    )
    if not points:
        return 1

    result = compute_homography(points)
    logger.info(
        "Homography from %d points: RMS error %.3f mm, max error %.3f mm",
        len(points), result.rms_error_mm, result.max_error_mm,
    )
    if result.rms_error_mm > 2.0:
        logger.warning("RMS error above 2 mm — check marker positions and re-measure")
    save_calibration(calibration_file, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
