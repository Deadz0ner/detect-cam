"""Region of interest — building the polygon and its precomputed helpers.

The ROI is the "do not enter" zone. We store it as a NumPy array of
(x, y) integer pixel coordinates — the vertices of a closed polygon.

Two ways to build one:
  - build_default_roi(): a hardcoded rectangle that covers the middle-bottom
    of the frame. Defined in fractional coords so it scales with resolution.
  - pick_roi_interactively(): the user clicks polygon vertices on the first
    frame and presses Enter to confirm.

Two precomputed helpers are also defined here because they live alongside
the polygon they describe:
  - build_roi_aabb(): the polygon's bounding rectangle. Used as a fast
    overlap filter in checks.py.
  - build_roi_mask(): a binary image where pixels inside the polygon are
    1 and everything else is 0. Used by the bbox-check mode in checks.py.
"""

import cv2
import numpy as np

from config import FPS_COLOR, ROI_COLOR


def build_default_roi(frame_w: int, frame_h: int) -> np.ndarray:
    """Fallback ROI — an axis-aligned rectangle as fractions of the frame.

    The fractions are constant, so the ROI sits in the same relative spot
    regardless of whether the source is 480p, 720p, or 1080p.

    Returns 4 vertices forming a rectangle in the middle-bottom of the frame
    (30%-70% width, 40%-95% height).
    """
    fractions = np.array([
        [0.30, 0.40],   # top-left
        [0.70, 0.40],   # top-right
        [0.70, 0.95],   # bottom-right
        [0.30, 0.95],   # bottom-left
    ])
    return (fractions * np.array([frame_w, frame_h])).astype(np.int32)


def pick_roi_interactively(first_frame: np.ndarray) -> np.ndarray:
    """Show the first frame, let the user click polygon vertices.

    Controls:
        left-click   → add a vertex
        Enter        → confirm (need at least 3 vertices)
        R            → reset and start over
        C            → fall back to the default ROI
        Esc          → abort the program
    """
    points: list[tuple[int, int]] = []
    window = "Pick ROI: click points, ENTER=confirm, R=reset, C=default, ESC=abort"

    def redraw() -> np.ndarray:
        # Repaint the frame with the polygon-so-far overlaid on top.
        canvas = first_frame.copy()
        for i, p in enumerate(points):
            cv2.circle(canvas, p, 5, ROI_COLOR, -1)
            if i > 0:
                cv2.line(canvas, points[i - 1], p, ROI_COLOR, 2)
        if len(points) >= 3:
            # Visually close the polygon by drawing the last→first edge.
            cv2.line(canvas, points[-1], points[0], ROI_COLOR, 1)
        cv2.putText(canvas, f"points: {len(points)}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, FPS_COLOR, 2)
        return canvas

    def on_mouse(event: int, x: int, y: int, flags: int, param: object) -> None:
        # OpenCV calls this on every mouse event; we only care about clicks.
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        cv2.imshow(window, redraw())
        key = cv2.waitKey(20) & 0xFF
        if key == 13 and len(points) >= 3:        # Enter
            break
        if key == ord("r"):
            points.clear()
        elif key == ord("c"):
            cv2.destroyWindow(window)
            return build_default_roi(first_frame.shape[1], first_frame.shape[0])
        elif key == 27:                           # Esc
            cv2.destroyWindow(window)
            raise SystemExit("ROI picker aborted.")

    cv2.destroyWindow(window)
    return np.array(points, dtype=np.int32)


def build_roi_aabb(roi: np.ndarray) -> tuple[int, int, int, int]:
    """Smallest axis-aligned rectangle that contains the polygon.

    Used as a *fast reject* before the precise mask check. If a person's
    bbox doesn't even touch this rectangle, it cannot touch the polygon
    inside it either — so the precise check can be skipped.

    Returns (x_min, y_min, x_max, y_max).
    """
    xs = roi[:, 0]
    ys = roi[:, 1]
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def build_roi_mask(roi: np.ndarray, frame_shape: tuple[int, int]) -> np.ndarray:
    """Rasterize the polygon into a binary mask the size of the frame.

    Each pixel inside the polygon becomes 1; everything else stays 0.
    Built once at startup, then sliced under each detection's bbox to
    answer "do they actually overlap?" pixel-accurately.

    `frame_shape` is (height, width).
    """
    mask = np.zeros(frame_shape, dtype=np.uint8)
    cv2.fillPoly(mask, [roi], 1)
    return mask
