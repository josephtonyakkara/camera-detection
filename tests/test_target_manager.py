"""Tests for pick target generation, selection strategies, workspace bounds,
and the M9 cross-frame duplicate-suppression lifecycle."""

from __future__ import annotations

import time

import pytest

from vision_system.config.models import RobotConfig, WorkspaceBounds
from vision_system.coordinates.transformer import IdentityTransformer
from vision_system.models.data import DetectionResult
from vision_system.targets.pick_target_manager import PickTargetManager

from tests.conftest import make_detection


def make_manager(
    strategy: str = "nearest",
    bounds: WorkspaceBounds | None = None,
    cooldown: float = 3.0,
) -> PickTargetManager:
    config = RobotConfig(
        target_selection=strategy,
        pick_z=-30.0,
        dedup_radius_mm=15.0,
        picked_cooldown_s=cooldown,
        workspace=bounds or WorkspaceBounds(x_min=0, x_max=1280, y_min=0, y_max=720),
    )
    return PickTargetManager(config, IdentityTransformer())


def make_result(centers: list[tuple[float, float]], frame_id: int = 1) -> DetectionResult:
    return DetectionResult(
        frame_id=frame_id,
        timestamp=time.time(),
        image_width=1280,
        image_height=720,
        detections=[make_detection(x, y) for x, y in centers],
    )


# --- candidate generation (dashboard view) ---


def test_generates_candidate_per_detection(detection_result: DetectionResult) -> None:
    targets = make_manager().generate_targets(detection_result)
    assert len(targets) == 3
    assert all(t.coordinate.z == -30.0 for t in targets)
    assert [t.target_id for t in targets] == [1, 2, 3]  # per-frame numbering


def test_candidate_numbering_stable_across_frames(detection_result: DetectionResult) -> None:
    manager = make_manager()
    first = manager.generate_targets(detection_result)
    second = manager.generate_targets(detection_result)
    assert [t.target_id for t in first] == [t.target_id for t in second]


def test_leftmost_strategy(detection_result: DetectionResult) -> None:
    targets = make_manager("leftmost").generate_targets(detection_result)
    assert targets[0].coordinate.x == 30


def test_highest_confidence_strategy(detection_result: DetectionResult) -> None:
    targets = make_manager("highest_confidence").generate_targets(detection_result)
    assert targets[0].confidence == 0.95


def test_out_of_workspace_targets_rejected(detection_result: DetectionResult) -> None:
    manager = make_manager(bounds=WorkspaceBounds(x_min=0, x_max=120, y_min=0, y_max=720))
    targets = manager.generate_targets(detection_result)
    assert len(targets) == 2  # detection at x=150 rejected


def test_empty_result_is_valid(detection_result: DetectionResult) -> None:
    detection_result.detections.clear()
    assert make_manager().generate_targets(detection_result) == []


def test_unknown_strategy_rejected() -> None:
    with pytest.raises(ValueError, match="target_selection"):
        make_manager("teleport")


# --- select_next lifecycle (M9) ---


def test_select_next_picks_nearest_and_marks_in_progress() -> None:
    manager = make_manager()
    target = manager.select_next(make_result([(100, 50), (30, 40)]), now=0.0)
    assert target is not None
    assert (target.coordinate.x, target.coordinate.y) == (30, 40)
    assert manager.in_progress_target_id == target.target_id


def test_no_second_target_while_in_progress() -> None:
    manager = make_manager()
    first = manager.select_next(make_result([(100, 50), (300, 200)]), now=0.0)
    assert first is not None
    # same parts seen again on later frames: nothing new dispatched
    assert manager.select_next(make_result([(100, 50), (300, 200)]), now=1.0) is None


def test_stationary_part_not_reoffered_during_cooldown() -> None:
    manager = make_manager(cooldown=5.0)
    target = manager.select_next(make_result([(100, 50)]), now=0.0)
    manager.notify_pick_complete(target.target_id, now=1.0)
    # part still visible at the same spot within cooldown: suppressed
    assert manager.select_next(make_result([(101, 51)]), now=2.0) is None


def test_failed_pick_reoffered_after_cooldown() -> None:
    manager = make_manager(cooldown=5.0)
    first = manager.select_next(make_result([(100, 50)]), now=0.0)
    manager.notify_pick_complete(first.target_id, now=1.0)
    second = manager.select_next(make_result([(100, 50)]), now=7.0)  # cooldown expired
    assert second is not None
    assert second.target_id == first.target_id + 1


def test_next_part_offered_after_pick_complete() -> None:
    manager = make_manager(cooldown=5.0)
    first = manager.select_next(make_result([(30, 40), (300, 200)]), now=0.0)
    assert (first.coordinate.x, first.coordinate.y) == (30, 40)
    manager.notify_pick_complete(first.target_id, now=1.0)
    # picked part removed; remaining part is dispatched while cooldown active
    second = manager.select_next(make_result([(300, 200)]), now=2.0)
    assert second is not None
    assert (second.coordinate.x, second.coordinate.y) == (300, 200)


def test_pick_complete_for_stale_id_ignored() -> None:
    manager = make_manager()
    target = manager.select_next(make_result([(100, 50)]), now=0.0)
    manager.notify_pick_complete(999, now=1.0)  # unknown id
    assert manager.in_progress_target_id == target.target_id


def test_send_failed_releases_target() -> None:
    manager = make_manager()
    result = make_result([(100, 50)])
    first = manager.select_next(result, now=0.0)
    manager.notify_send_failed(first.target_id)
    assert manager.in_progress_target_id is None
    retry = manager.select_next(result, now=1.0)
    assert retry is not None
    assert (retry.coordinate.x, retry.coordinate.y) == (100, 50)
