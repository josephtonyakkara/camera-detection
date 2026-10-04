"""Application orchestrator wiring all modules together.

Owns the processing loop:
    CameraManager -> ImageProcessor -> PartDetector -> PickTargetManager -> RobotInterface

Later milestones extend this with the web UI (M3/M11) and OPC UA robot
interface (M10) without changing the module wiring pattern.
"""

from __future__ import annotations

import logging
import time

import cv2

from vision_system.camera.manager import CameraManager
from vision_system.config.models import AppConfig
from vision_system.coordinates.calibration import load_transformer
from vision_system.coordinates.transformer import CoordinateTransformer
from vision_system.detection.base import PartDetector
from vision_system.detection.opencv_detector import OpenCVDetector
from vision_system.detection.reference_loader import load_reference_set
from vision_system.models.data import DetectionResult, PickTarget, ProcessingMode
from vision_system.processing.image_processor import ImageProcessor
from vision_system.communication.base import RobotError, RobotInterface
from vision_system.communication.mock_robot import MockRobot
from vision_system.targets.pick_target_manager import PickTargetManager
from vision_system.utils.paths import resolve
from vision_system.visualization.overlay import draw_overlay
from vision_system.models.live_state import LiveState

logger = logging.getLogger(__name__)


def create_detector(detector_type: str) -> PartDetector:
    """Factory for the configured detector implementation."""
    if detector_type == "opencv":
        return OpenCVDetector()
    raise ValueError(f"Unknown detector type: {detector_type!r}")


def create_robot(config: AppConfig) -> RobotInterface:
    """Factory for the configured robot communication implementation."""
    interface_type = config.communication.interface
    if interface_type == "mock":
        return MockRobot()
    if interface_type == "opcua":
        # imported lazily so environments without asyncua can run with the mock
        from vision_system.communication.opcua_server import OpcUaRobotServer

        return OpcUaRobotServer(config.communication.opcua)
    raise ValueError(f"Unknown robot interface: {interface_type!r}")


class VisionApplication:
    """Builds and runs the vision pipeline from an AppConfig."""

    def __init__(
        self,
        config: AppConfig,
        transformer: CoordinateTransformer | None = None,
        live_state: LiveState | None = None,
    ) -> None:
        self._config = config
        self._mode = ProcessingMode(config.vision.processing_mode)
        self._camera = CameraManager(config.camera)
        self._processor = ImageProcessor()
        self._detector = create_detector(config.vision.detector)
        # HomographyTransformer when calibrated; IdentityTransformer fallback otherwise
        self._transformer = transformer or load_transformer(
            resolve(config.system.calibration_file), config.robot.pick_z
        )
        self._targets = PickTargetManager(config.robot, self._transformer)
        self._robot = create_robot(config)
        self._live_state = live_state
        self._running = False
        self._last_ack_id: int | None = None
        self._fps = 0.0
        self._fps_frames = 0
        self._fps_t0 = time.perf_counter()
        self._last_annotated = None

    def start(self) -> None:
        """Load references, connect camera and robot."""
        references = load_reference_set(
            resolve(self._config.vision.parts_dir), self._config.vision.active_part
        )
        self._detector.configure(
            references,
            self._config.vision.confidence_threshold,
            self._config.vision.detection_params,
        )
        self._camera.start()
        self._robot.connect()
        self._running = True
        logger.info(
            "Vision application started (mode=%s, part=%s)",
            self._mode.value,
            references.part_name,
        )

    def process_one_frame(self) -> tuple[DetectionResult, list[PickTarget]]:
        """Run one full pipeline iteration and return its structured outputs."""
        frame = self._camera.get_frame()
        processed = self._processor.process(frame)
        result = self._detector.detect(processed)
        self._robot.publish_detection_count(result.detection_count)

        status = self._robot.get_robot_status()
        if (
            status.last_pick_target_id is not None
            and status.last_pick_target_id != self._last_ack_id
        ):
            self._targets.notify_pick_complete(status.last_pick_target_id)
            self._last_ack_id = status.last_pick_target_id

        candidates = self._targets.generate_targets(result)
        if self._robot.is_robot_ready():
            target = self._targets.select_next(result)
            if target is not None:
                try:
                    self._robot.send_pick_target(target)
                except RobotError as exc:
                    logger.error("Failed to send target %d: %s", target.target_id, exc)
                    self._targets.notify_send_failed(target.target_id)

        self._update_fps()
        annotated = self._publish(frame.image, result, candidates)
        self._last_annotated = annotated
        return result, candidates

    def _update_fps(self) -> None:
        self._fps_frames += 1
        elapsed = time.perf_counter() - self._fps_t0
        if elapsed >= 1.0:
            self._fps = self._fps_frames / elapsed
            self._fps_frames = 0
            self._fps_t0 = time.perf_counter()

    def _publish(self, image, result: DetectionResult, targets: list[PickTarget]):
        """Annotate the frame and push it to the web LiveState if enabled."""
        needs_overlay = self._live_state is not None or self._mode is ProcessingMode.DEBUG
        if not needs_overlay:
            return None
        annotated = draw_overlay(image, result, targets, fps=self._fps)
        if self._live_state is not None:
            ok, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                self._live_state.publish(
                    buffer.tobytes(),
                    result,
                    targets,
                    self._robot.get_robot_status(),
                    self._fps,
                    pending_target_id=self._targets.in_progress_target_id,
                )
        return annotated

    def run(self) -> None:
        """Run the configured processing mode until stopped."""
        self.start()
        debug = self._mode is ProcessingMode.DEBUG
        try:
            if self._mode is ProcessingMode.SINGLE_FRAME:
                result, targets = self.process_one_frame()
                logger.info(
                    "Single frame processed: %d part(s), %d target(s)",
                    result.detection_count,
                    len(targets),
                )
                return
            while self._running:
                self.process_one_frame()
                if debug and self._last_annotated is not None:
                    cv2.imshow("vision_system (debug)", self._last_annotated)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        logger.info("Debug window closed by user")
                        break
        finally:
            if debug:
                cv2.destroyAllWindows()
            self.stop()

    def request_stop(self) -> None:
        """Ask the run loop to exit after the current frame (thread-safe)."""
        self._running = False

    def get_communication_info(self):
        """Delegate to the robot interface (None for interfaces without introspection)."""
        return self._robot.get_communication_info()

    def stop(self) -> None:
        self._running = False
        if self._live_state is not None:
            self._live_state.mark_stopped()
        self._camera.stop()
        self._robot.disconnect()
        logger.info("Vision application stopped")
