"""Milestone 4/5 detection validation tool.

Runs the configured detector on saved images (default: all images of the
active reference set) and writes annotated results to logs/detect_check/.

Usage (from project root, venv active):
    python scripts/detect_check.py                 # run on active part's reference images
    python scripts/detect_check.py img1.jpg ...    # run on specific images
    python scripts/detect_check.py --live          # run on one live camera frame
    python scripts/detect_check.py --live --frames 30   # count stability over 30 frames
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cv2

from vision_system.app import create_detector
from vision_system.config.loader import load_config
from vision_system.detection.reference_loader import load_reference_set
from vision_system.models.data import FrameData, ProcessedFrame
from vision_system.utils.logging_setup import setup_logging
from vision_system.utils.paths import resolve
from vision_system.visualization.overlay import draw_overlay

logger = logging.getLogger("detect_check")


def frame_from_image(image, frame_id: int) -> ProcessedFrame:
    height, width = image.shape[:2]
    source = FrameData(
        frame_id=frame_id, timestamp=time.time(), image=image, width=width, height=height
    )
    return ProcessedFrame(source=source, image=image)


def run_stability(detector, config, out_dir: Path, frames: int) -> None:
    """Detect over N consecutive live frames and report count consistency."""
    from collections import Counter

    from vision_system.camera.manager import CameraManager

    camera = CameraManager(config.camera)
    camera.start()
    counts: list[int] = []
    last_annotated = None
    try:
        for i in range(frames):
            frame = camera.get_frame()
            result = detector.detect(frame_from_image(frame.image, i + 1))
            counts.append(result.detection_count)
            last_annotated = draw_overlay(frame.image, result)
    finally:
        camera.stop()

    histogram = Counter(counts)
    mode_count, mode_hits = histogram.most_common(1)[0]
    stability = 100.0 * mode_hits / len(counts)
    logger.info("Counts per frame: %s", counts)
    logger.info("Count histogram: %s", dict(sorted(histogram.items())))
    logger.info(
        "Dominant count = %d in %d/%d frames (%.1f%% stable)",
        mode_count,
        mode_hits,
        len(counts),
        stability,
    )
    if last_annotated is not None:
        path = out_dir / "stability_last_annotated.jpg"
        cv2.imwrite(str(path), last_annotated)
        logger.info("Last annotated frame: %s", path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*", help="image files to test (default: reference set)")
    parser.add_argument("--live", action="store_true", help="grab live camera frame(s) instead")
    parser.add_argument(
        "--frames", type=int, default=1, metavar="N", help="with --live: frames for count stability"
    )
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.system.log_level)
    out_dir = resolve(config.system.log_dir) / "detect_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    references = load_reference_set(
        resolve(config.vision.parts_dir), config.vision.active_part
    )
    detector = create_detector(config.vision.detector)
    detector.configure(
        references, config.vision.confidence_threshold, config.vision.detection_params
    )

    if args.live:
        if args.frames > 1:
            run_stability(detector, config, out_dir, args.frames)
            return 0
        from vision_system.camera.manager import CameraManager

        camera = CameraManager(config.camera)
        camera.start()
        try:
            frame = camera.get_frame()
            sources: list[tuple[str, object]] = [("live", frame.image)]
        finally:
            camera.stop()
    else:
        paths = [Path(p) for p in args.images] if args.images else references.image_paths
        sources = [(p.stem, cv2.imread(str(p))) for p in paths]

    total_images = 0
    total_detections = 0
    for name, image in sources:
        if image is None:
            logger.warning("Skipping unreadable image: %s", name)
            continue
        result = detector.detect(frame_from_image(image, total_images + 1))
        total_images += 1
        total_detections += result.detection_count
        for detection in result.detections:
            logger.info(
                "%s: %s conf=%.3f center=(%.0f, %.0f) area=%.0fpx dist=%.4f",
                name,
                detection.class_name,
                detection.confidence,
                detection.center_x_px,
                detection.center_y_px,
                detection.metadata.get("area_px", -1),
                detection.metadata.get("shape_distance", -1),
            )
        if result.detection_count == 0:
            logger.warning("%s: no detections", name)
        annotated = draw_overlay(image, result)
        cv2.imwrite(str(out_dir / f"{name}_annotated.jpg"), annotated)

    logger.info(
        "Done: %d detection(s) across %d image(s); annotated output in %s",
        total_detections,
        total_images,
        out_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
