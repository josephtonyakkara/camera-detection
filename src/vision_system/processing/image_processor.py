"""Pre-processes raw frames into detector-ready frames.

Milestone 1 provides a pass-through pipeline; filters (blur, normalization,
color conversion) are added in Milestone 3/4 as detection needs emerge.
"""

from __future__ import annotations

from vision_system.models.data import FrameData, ProcessedFrame


class ImageProcessor:
    """Applies the configured pre-processing chain to a frame."""

    def process(self, frame: FrameData) -> ProcessedFrame:
        """Return a ProcessedFrame for the detector. Currently pass-through."""
        return ProcessedFrame(source=frame, image=frame.image, operations=[])
