# ROI (Region of Interest)

The "do not enter" zone. Stored as a NumPy array of `(x, y)` integer pixel
coordinates — the vertices of a closed polygon.

```python
roi = np.array([[400, 300], [700, 300], [700, 600], [400, 600]], dtype=np.int32)
# A 4-point rectangle in pixel space.
```

There are two ways to build this array.

## Default ROI

[detect.py:26-34](../detect.py#L26-L34)

A polygon defined as **fractions of the frame**, then multiplied by the
frame's width and height. Fractions instead of fixed pixels means the ROI
sits in the same relative spot regardless of resolution (480p, 720p, 1080p
all work).

The default fractions cover the middle-bottom of the frame:

```
[0.30, 0.40]   top-left      → 30% across, 40% down
[0.70, 0.40]   top-right     → 70% across, 40% down
[0.70, 0.95]   bottom-right
[0.30, 0.95]   bottom-left
```

Used when `--pick-roi` is **not** passed.

## Interactive ROI

[detect.py:37-87](../detect.py#L37-L87)

When `--pick-roi` is passed, the first frame is shown frozen in a window.
The user clicks polygon vertices; OpenCV's mouse callback appends each click
to a `points` list. After ≥3 points the user presses Enter to confirm and
the function returns `np.array(points, dtype=np.int32)`.

Controls:

| Key / mouse | Action |
|---|---|
| Left-click | Add a vertex |
| Enter | Confirm (need ≥3 points) |
| R | Reset and start over |
| C | Use the default ROI instead |
| Esc | Abort the program |

## Why a polygon and not a rectangle

`cv2.pointPolygonTest` works on any closed polygon, so a polygon costs the
same as a rectangle but generalizes to non-rectangular zones (a doorway, an
L-shaped corridor, a triangular alcove). Rectangles would be a special case
of "polygon with 4 axis-aligned points".

## Lifetime

The ROI is built **once**, before the loop, and reused on every frame. It
doesn't change during a run.
