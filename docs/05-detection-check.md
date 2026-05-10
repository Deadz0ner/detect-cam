# Detection check

Given a person bbox from YOLO, how do we decide if that person is "inside the
ROI"? Two modes, selected by the `--check` CLI flag. All the code for this
lives in [checks.py](../checks.py).

## Mode 1 — `feet` (default)

A single representative point is tested against the polygon.

### Step 1 — Pick the point

[checks.py](../checks.py) → `feet_point`

```python
def feet_point(x1, y1, x2, y2):
    return ((x1 + x2) // 2, y2)
```

Bottom-center of the bounding box. Conceptually: where the person's feet
are touching the floor.

```
   (x1, y1) ┌─────────┐
            │         │
            │  person │
            │         │
            └────●────┘ (x2, y2)
              (feet)
```

Deeper reasoning for why feet rather than centroid or head:
[09-why-feet-check.md](09-why-feet-check.md).

### Step 2 — Polygon test

[checks.py](../checks.py) → `is_inside_roi`

```python
def is_inside_roi(point, roi):
    return cv2.pointPolygonTest(roi, point, measureDist=False) >= 0
```

`cv2.pointPolygonTest` returns `+1` inside, `0` on edge, `-1` outside. We
treat "inside or on the edge" as a hit.

### When `feet` works well

- Surveillance camera that sees the full body
- ROI defined on the floor plane
- Person standing upright

### When `feet` fails

Close-range scenes where the lower body is cropped (laptop webcam, close
selfie). The bbox bottom sits at the chest, not the feet, so the chosen
point lands in the wrong place — sometimes outside the ROI even though
the person is clearly "in" it.

## Mode 2 — `bbox`

Triggers if **any pixel of the bounding box overlaps the ROI.** Implemented
as a two-step check (broad-phase then narrow-phase), which is how every
collision-detection system works.

### Step 1 — AABB fast reject

[checks.py](../checks.py) → `aabb_overlap`

```python
def aabb_overlap(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    return not (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)
```

The textbook axis-aligned rectangle overlap test: two rectangles overlap
unless one is completely on one side of the other. Four comparisons, O(1).

We compare the **bbox** to the **polygon's bounding rectangle** (computed
once at startup by `build_roi_aabb()` in [roi.py](../roi.py)). If the
rectangles don't overlap, the bbox can't possibly touch the polygon inside
the bounding rectangle either — return False immediately.

Full explanation of why this works for any polygon, and what "maybe" means:
[10-aabb-fastreject.md](10-aabb-fastreject.md).

### Step 2 — Mask check (only if step 1 said "maybe")

[checks.py](../checks.py) → `bbox_overlaps_roi`

```python
return bool(roi_mask[by1:by2, bx1:bx2].any())
```

The polygon is rasterised once at startup into a binary mask
(`build_roi_mask()` in [roi.py](../roi.py)). When step 1 can't rule out
overlap, we slice the mask under the bbox and ask "is any pixel set?".

For **rectangular ROIs** (the default) this step is skipped entirely —
the polygon equals its bounding rectangle, so step 1's answer is already
exact. We pass `roi_mask=None` to signal this.

### When `bbox` works well

- Close-range scenes (only head/shoulders visible)
- Partial occlusion of the lower body
- ROIs defined on the image plane rather than the floor

### When `bbox` over-triggers

A person standing well outside the zone whose **arm** or **bag** crosses
the ROI line will alert. In production this is usually mitigated with a
coverage threshold — *"alert if at least 20% of the bbox area is inside
the ROI"* — instead of plain "any overlap." That's a small extension of
the mask approach, not a different one.

## Aggregation

Either mode produces a per-detection boolean. The per-frame loop OR's those
booleans into a single verdict — *"is at least one person inside the ROI
right now?"*:

```python
person_in_roi = False
for box in boxes:
    ...
    if inside:
        person_in_roi = True
```

One frame, one verdict, regardless of how many people are visible or which
mode is active.

## How to switch

```bash
python detect.py --source clip.mp4                 # feet (default)
python detect.py --source clip.mp4 --check bbox    # any bbox overlap
```

The active mode is shown in the top-left of the live window
(`check: feet` / `check: bbox`) so you can confirm at a glance.
