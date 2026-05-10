"""Drawing helpers — the visual overlays painted on each frame.

Everything here mutates `frame` in place. There is no separate canvas — the
same NumPy array we hand to YOLO is the one we paint on, then either show
in a window or write to disk.
"""

import cv2
import numpy as np

from config import FPS_COLOR, ROI_COLOR


def draw_detection(
    frame: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: tuple[int, int, int],
    label: str,
    anchor_point: tuple[int, int] | None,
) -> None:
    """Paint one person's annotations onto the frame in place.

    - Coloured bounding-box rectangle (green outside ROI, red inside).
    - Optional anchor-point dot (drawn in feet mode at the feet point;
      bbox mode passes None so no dot is drawn).
    - Class label text above the box, clamped to stay inside the frame.
    """
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    if anchor_point is not None:
        cv2.circle(frame, anchor_point, 4, color, -1)
    cv2.putText(frame, label, (x1, max(y1 - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def draw_roi(frame: np.ndarray, roi: np.ndarray) -> None:
    """Draw the ROI as a closed polygon outline.

    Done after the detection boxes so the ROI always stays visible on top.
    """
    cv2.polylines(frame, [roi], isClosed=True, color=ROI_COLOR, thickness=2)


def draw_overlay(
    frame: np.ndarray, fps: float, frame_idx: int, check_mode: str,
) -> None:
    """Top-left status overlay: live FPS, frame number, and check mode.

    The check_mode label lets you tell at a glance whether `feet` or `bbox`
    logic is active — useful when comparing the two modes on the same video.
    """
    text = f"FPS: {fps:.1f}  frame: {frame_idx}  check: {check_mode}"
    cv2.putText(frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, FPS_COLOR, 2)
