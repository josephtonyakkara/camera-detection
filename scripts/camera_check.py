"""Milestone 2 camera validation tool.

Usage (from project root, venv active):
    python scripts/camera_check.py            # live preview; S saves frame, Q/ESC quits
    python scripts/camera_check.py --save 3   # headless: save 3 frames and report
    python scripts/camera_check.py --list     # probe all USB cameras, save one snapshot each
    python scripts/camera_check.py --device 1 # preview a specific device index

Saved frames go to logs/camera_check/.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cv2

from vision_system.camera.manager import CameraManager
from vision_system.camera.usb_camera import enumerate_usb_cameras
from vision_system.config.loader import load_config
from vision_system.utils.logging_setup import setup_logging
from vision_system.utils.paths import resolve

logger = logging.getLogger("camera_check")


def list_cameras(out_dir: Path) -> None:
    logger.info("Probing USB camera indices 0-9 ...")
    probes = enumerate_usb_cameras(with_snapshot=True)
    if not probes:
        logger.error("No working USB cameras found")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    for probe in probes:
        path = out_dir / f"device_{probe.device_index}.jpg"
        cv2.imwrite(str(path), probe.snapshot)
        logger.info(
            "Device %d: %dx%d  ->  snapshot %s",
            probe.device_index,
            probe.width,
            probe.height,
            path,
        )
    logger.info(
        "Set the chosen index as 'device_index' in config/camera.yaml"
    )


def save_frame(out_dir: Path, image, frame_id: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"frame_{frame_id:05d}_{int(time.time())}.jpg"
    cv2.imwrite(str(path), image)
    logger.info("Saved %s", path)
    return path


def run_headless(camera: CameraManager, out_dir: Path, count: int) -> None:
    for _ in range(count):
        frame = camera.get_frame()
        logger.info(
            "Frame %d: %dx%d %s, mean brightness %.1f",
            frame.frame_id,
            frame.width,
            frame.height,
            frame.color_format,
            float(frame.image.mean()),
        )
        save_frame(out_dir, frame.image, frame.frame_id)


def run_preview(camera: CameraManager, out_dir: Path) -> None:
    logger.info("Live preview: S = save frame, Q/ESC = quit")
    fps_t0, fps_frames, fps = time.time(), 0, 0.0
    while True:
        frame = camera.get_frame()
        fps_frames += 1
        if time.time() - fps_t0 >= 1.0:
            fps = fps_frames / (time.time() - fps_t0)
            fps_t0, fps_frames = time.time(), 0
        display = frame.image.copy()
        cv2.putText(
            display,
            f"frame {frame.frame_id}  {frame.width}x{frame.height}  {fps:.1f} fps",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.imshow("camera_check", display)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("s"):
            save_frame(out_dir, frame.image, frame.frame_id)
    cv2.destroyAllWindows()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", type=int, metavar="N", help="headless: save N frames and exit")
    parser.add_argument("--list", action="store_true", help="probe all USB cameras and exit")
    parser.add_argument("--device", type=int, metavar="IDX", help="override configured device_index")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.system.log_level)
    out_dir = resolve(config.system.log_dir) / "camera_check"

    if args.list:
        list_cameras(out_dir)
        return 0

    if args.device is not None:
        config.camera.device_index = args.device

    camera = CameraManager(config.camera)
    camera.start()
    try:
        if args.save:
            run_headless(camera, out_dir, args.save)
        else:
            run_preview(camera, out_dir)
    finally:
        camera.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
