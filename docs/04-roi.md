# ROI (Region of Interest)

The "do not enter" zone. Stored as a NumPy array of `(x, y)` integer pixel
coordinates — the vertices of a closed polygon. All construction lives in
[roi.py](../roi.py).

```python
roi = np.array([[400, 300], [700, 300], [700, 600], [400, 600]], dtype=np.int32)
# A 4-point rectangle in pixel space.
```

There are two ways to build this array.

## Default ROI

[roi.py](../roi.py) → `build_default_roi`

A polygon defined as **fractions of the frame**, then multiplied by the
frame's width and height. Fractions instead of fixed pixels means the
ROI sits in the same relative spot regardless of resolution (480p, 720p,
1080p all work).

The default fractions cover the middle-bottom of the frame:

```
[0.30, 0.40]   top-left      → 30% across, 40% down
[0.70, 0.40]   top-right     → 70% across, 40% down
[0.70, 0.95]   bottom-right
[0.30, 0.95]   bottom-left
```

Used when `--pick-roi` is **not** passed. Because all four points have
just two unique x-values and two unique y-values, this is an axis-aligned
rectangle — which the rest of the pipeline can take advantage of (see
[10-aabb-fastreject.md](10-aabb-fastreject.md)).

## Interactive ROI

[roi.py](../roi.py) → `pick_roi_interactively`

When `--pick-roi` is passed, the first frame is shown frozen in a window.
The user clicks polygon vertices; OpenCV's mouse callback appends each
click to a `points` list. After ≥3 points the user presses Enter to
confirm and the function returns `np.array(points, dtype=np.int32)`.

Controls:

| Key / mouse | Action |
|---|---|
| Left-click | Add a vertex |
| Enter | Confirm (need ≥3 points) |
| R | Reset and start over |
| C | Use the default ROI instead |
| Esc | Abort the program |

## Precomputed helpers

Two helpers are also in [roi.py](../roi.py), built once at startup:

- `build_roi_aabb(roi)` — the smallest axis-aligned rectangle that
  contains the polygon. Used as a cheap overlap filter in
  [checks.py](../checks.py). Always built.
- `build_roi_mask(roi, frame_shape)` — a binary image where pixels
  inside the polygon are `1` and everything else is `0`. Used by the
  precise overlap check. Only built when the ROI is **not** an
  axis-aligned rectangle, since for rectangles the AABB answer is exact
  and no mask is needed.

## Why a polygon and not a rectangle

`cv2.pointPolygonTest` works on any closed polygon, so a polygon costs the
same as a rectangle but generalises to non-rectangular zones (a doorway,
an L-shaped corridor, a triangular alcove). Rectangles are a special case
that we exploit via the rectangular-ROI shortcut in
[checks.py](../checks.py).

## Lifetime

The ROI (and its helpers) are built **once**, before the loop, and reused
on every frame. They don't change during a run.
