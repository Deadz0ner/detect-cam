"""Deciding whether a detected person is "inside" the ROI.

Two strategies, selected at runtime by the --check CLI flag:

  feet → bottom-center of the bbox must be inside the polygon.
         Right answer for surveillance-style cameras viewing the whole
         body standing on a floor. See docs/09-why-feet-check.md.

  bbox → any pixel of the bbox must overlap the ROI.
         Useful for close-range scenes (e.g. webcam at face level) where
         the feet aren't visible. Uses a two-step check: a cheap AABB
         rectangle-overlap reject, then a precise mask check only when
         the AABB couldn't rule it out. See docs/10-aabb-fastreject.md.
"""

import cv2
import numpy as np


# ============================================================================
# Mode 1 — feet point in polygon
# ============================================================================


def feet_point(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    """Bottom-center of the bbox.

    Stands in for where the person's feet are touching the floor. The right
    anchor for floor-plane ROIs viewed by a surveillance camera. Detailed
    reasoning: docs/09-why-feet-check.md.
    """
    return ((x1 + x2) // 2, y2)


def is_inside_roi(point: tuple[int, int], roi: np.ndarray) -> bool:
    """Point-in-polygon test using OpenCV.

    cv2.pointPolygonTest returns +1 inside, 0 on edge, -1 outside; we treat
    "inside or on edge" (>= 0) as a hit.
    """
    return cv2.pointPolygonTest(roi, point, measureDist=False) >= 0


# ============================================================================
# Mode 2 — any pixel of bbox overlaps ROI
#
# Implemented as a two-step (broad-phase + narrow-phase) check:
#
#   Step 1 — AABB fast reject.
#       Compare the bbox rectangle to the polygon's bounding rectangle
#       using 4 inequalities. If they don't overlap at all, the bbox
#       cannot possibly overlap the polygon inside the bounding
#       rectangle. Return False immediately.
#
#   Step 2 — Pixel-precise mask check (polygon ROIs only).
#       Step 1's "maybe" can be a false alarm — the bbox might sit in a
#       corner of the bounding rectangle that's outside the polygon
#       itself. Slice the precomputed mask under the bbox and ask
#       "is any pixel inside the polygon?".
#
#       For rectangular ROIs the polygon IS its bounding rectangle, so
#       step 1's answer is already exact and step 2 is skipped (we pass
#       roi_mask=None in that case).
# ============================================================================


def aabb_overlap(
    x1: int, y1: int, x2: int, y2: int,
    rx1: int, ry1: int, rx2: int, ry2: int,
) -> bool:
    """Classic axis-aligned rectangle overlap test.

    Two rectangles overlap unless one is completely on one side of the
    other. Four comparisons, O(1), no allocations. This is the textbook
    AABB algorithm every collision-detection system starts with.
    """
    return not (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)


def bbox_overlaps_roi(
    x1: int, y1: int, x2: int, y2: int,
    roi_aabb: tuple[int, int, int, int],
    roi_mask: np.ndarray | None,
) -> bool:
    """Does any part of the bbox overlap the ROI?

    Args:
        x1, y1, x2, y2: bounding box corners in pixel coords.
        roi_aabb: bounding rectangle of the ROI polygon (see roi.py).
        roi_mask: binary mask of the polygon (see roi.py), or None when
            the ROI is itself an axis-aligned rectangle.
    """
    # ---- Step 1: AABB fast reject ----
    # If the bbox's rectangle doesn't touch the polygon's bounding
    # rectangle, no part of the bbox can be inside the polygon. Return
    # False without doing the expensive pixel check.
    if not aabb_overlap(x1, y1, x2, y2, *roi_aabb):
        return False

    # ---- Rectangular-ROI shortcut ----
    # When the ROI is itself an axis-aligned rectangle, its bounding
    # rectangle IS the polygon. Step 1 has already given the exact answer.
    if roi_mask is None:
        return True

    # ---- Step 2: pixel-precise mask check ----
    # The polygon might not fill its bounding rectangle — the bbox could
    # sit in an empty corner. Slice the mask under the bbox and ask if
    # any pixel is set (i.e. inside the polygon).
    h, w = roi_mask.shape
    bx1, by1 = max(x1, 0), max(y1, 0)
    bx2, by2 = min(x2, w), min(y2, h)
    if bx1 >= bx2 or by1 >= by2:
        # The bbox lies entirely outside the frame — nothing to check.
        return False
    return bool(roi_mask[by1:by2, bx1:bx2].any())
