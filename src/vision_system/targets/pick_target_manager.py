"""Converts detections into validated pick targets with cross-frame memory.

Selection strategy is configuration-driven (robot.target_selection). The
manager remembers dispatched targets by robot-space location so a stationary
part is offered to the robot exactly once:

    AVAILABLE -> select_next() dispatches it -> IN_PROGRESS (suppressed)
    -> notify_pick_complete() -> COOLDOWN (suppressed for picked_cooldown_s)
    -> location free again; if a part is still detected there, it is
       re-offered with a warning (likely failed pick).

Only one target is in flight at a time, matching the robot's
one-request/one-target handshake.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from vision_system.config.models import RobotConfig
from vision_system.coordinates.transformer import CoordinateTransformer, TransformError
from vision_system.models.data import Detection, DetectionResult, PickTarget, RobotCoordinate

logger = logging.getLogger(__name__)

_ORIGIN = RobotCoordinate(0.0, 0.0, 0.0)

# Strategy: key function ordering candidate (coordinate, detection) tuples; first wins.
_STRATEGIES: dict[str, Callable[[tuple[RobotCoordinate, Detection]], float]] = {
    "nearest": lambda c: math.hypot(c[0].x - _ORIGIN.x, c[0].y - _ORIGIN.y),
    "leftmost": lambda c: c[0].x,
    "rightmost": lambda c: -c[0].x,
    "highest_confidence": lambda c: -c[1].confidence,
}


@dataclass
class _Cooldown:
    target_id: int
    x: float
    y: float
    until: float


class PickTargetManager:
    """Transforms, validates, orders, dispatches, and deduplicates pick targets."""

    def __init__(self, config: RobotConfig, transformer: CoordinateTransformer) -> None:
        if config.target_selection not in _STRATEGIES:
            raise ValueError(
                f"Unknown target_selection {config.target_selection!r}; "
                f"expected one of {sorted(_STRATEGIES)}"
            )
        self._config = config
        self._transformer = transformer
        self._next_target_id = 1
        self._in_progress: tuple[int, RobotCoordinate] | None = None
        self._cooldowns: list[_Cooldown] = []

    @property
    def in_progress_target_id(self) -> int | None:
        return self._in_progress[0] if self._in_progress else None

    def _valid_candidates(self, result: DetectionResult) -> list[tuple[RobotCoordinate, Detection]]:
        """Transform, bounds-check, and strategy-order all detections."""
        candidates: list[tuple[RobotCoordinate, Detection]] = []
        for detection in result.detections:
            try:
                coord = self._transformer.image_to_robot(
                    detection.center_x_px, detection.center_y_px
                )
            except TransformError as exc:
                logger.warning("Skipping detection: transform failed (%s)", exc)
                continue
            coord = RobotCoordinate(x=coord.x, y=coord.y, z=self._config.pick_z)
            if not self._config.workspace.contains(coord.x, coord.y):
                logger.warning(
                    "Rejecting target outside workspace: (%.1f, %.1f)", coord.x, coord.y
                )
                continue
            candidates.append((coord, detection))
        candidates.sort(key=_STRATEGIES[self._config.target_selection])
        return candidates

    def _near(self, coord: RobotCoordinate, x: float, y: float) -> bool:
        return math.hypot(coord.x - x, coord.y - y) <= self._config.dedup_radius_mm

    def _expire_cooldowns(
        self, now: float, candidates: list[tuple[RobotCoordinate, Detection]]
    ) -> None:
        still_active: list[_Cooldown] = []
        for cooldown in self._cooldowns:
            if now < cooldown.until:
                still_active.append(cooldown)
                continue
            if any(self._near(coord, cooldown.x, cooldown.y) for coord, _ in candidates):
                logger.warning(
                    "Part still detected near picked target %d at (%.1f, %.1f) after "
                    "cooldown - re-offering (failed pick?)",
                    cooldown.target_id,
                    cooldown.x,
                    cooldown.y,
                )
        self._cooldowns = still_active

    def _suppressed(self, coord: RobotCoordinate) -> bool:
        if self._in_progress is not None:
            in_progress_coord = self._in_progress[1]
            if self._near(coord, in_progress_coord.x, in_progress_coord.y):
                return True
        return any(self._near(coord, c.x, c.y) for c in self._cooldowns)

    def generate_targets(self, result: DetectionResult) -> list[PickTarget]:
        """All valid candidates for this frame (dashboard view).

        Numbered 1..n per frame; real target ids are assigned by select_next()
        at dispatch time. An empty list is a valid outcome.
        """
        return [
            PickTarget(
                target_id=index,
                coordinate=coord,
                class_name=detection.class_name,
                confidence=detection.confidence,
                source_frame_id=result.frame_id,
            )
            for index, (coord, detection) in enumerate(self._valid_candidates(result), start=1)
        ]

    def select_next(self, result: DetectionResult, now: float | None = None) -> PickTarget | None:
        """Pick the single best new target, mark it in-progress, or return None.

        Returns None while a target is in flight or every candidate is
        suppressed (in-progress/cooldown locations).
        """
        now = time.time() if now is None else now
        candidates = self._valid_candidates(result)
        self._expire_cooldowns(now, candidates)
        if self._in_progress is not None:
            return None
        for coord, detection in candidates:
            if self._suppressed(coord):
                continue
            target = PickTarget(
                target_id=self._next_target_id,
                coordinate=coord,
                class_name=detection.class_name,
                confidence=detection.confidence,
                source_frame_id=result.frame_id,
            )
            self._next_target_id += 1
            self._in_progress = (target.target_id, coord)
            return target
        return None

    def notify_pick_complete(self, target_id: int, now: float | None = None) -> None:
        """Robot acknowledged the pick: start the location cooldown."""
        now = time.time() if now is None else now
        if self._in_progress is None or self._in_progress[0] != target_id:
            logger.warning("Pick-complete for unknown/stale target %d ignored", target_id)
            return
        _, coord = self._in_progress
        self._cooldowns.append(
            _Cooldown(
                target_id=target_id,
                x=coord.x,
                y=coord.y,
                until=now + self._config.picked_cooldown_s,
            )
        )
        self._in_progress = None
        logger.info("Target %d picked; location cooldown started", target_id)

    def notify_send_failed(self, target_id: int) -> None:
        """Dispatch failed: release the in-progress slot so it can be retried."""
        if self._in_progress is not None and self._in_progress[0] == target_id:
            self._in_progress = None
            logger.info("Target %d released after failed send", target_id)
