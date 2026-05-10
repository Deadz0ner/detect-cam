# Detection check

Given a person box from YOLO, how do we decide if that person is "inside the
ROI"? Two modes, selected by the `--check` flag.

## Mode 1 — `feet` (default)

A single representative point is tested against the polygon.

### Step 1 — Pick the point

[detect.py:90-92](../detect.py#L90-L92)

```python
def feet_point(x1, y1, x2, y2):
    return ((x1 + x2) // 2, y2)
```

The bottom-center of the bounding box. Conceptually: where the person's
feet are touching the floor.

```
   (x1, y1) ┌─────────┐
            │         │
            │  person │
            │         │
            └────●────┘ (x2, y2)
              (feet)
```

### Step 2 — Polygon test

[detect.py:95-96](../detect.py#L95-L96)

```python
def is_inside_roi(point, roi):
    return cv2.pointPolygonTest(roi, point, measureDist=False) >= 0
```

`cv2.pointPolygonTest` returns `+1` inside, `0` on edge, `-1` outside. We
treat "inside or on edge" as a hit.

### When `feet` works well

- Surveillance camera that sees the full body
- ROI defined on the floor plane
- Person standing upright — see [09-why-feet-check.md](09-why-feet-check.md)

### When `feet` fails

Close-range scenes where the lower body is cropped off (laptop webcam,
chest-mounted camera). The bbox bottom is at the chest, not the feet, so
the chosen point lands in the wrong place — sometimes outside the ROI even
though the person is clearly "in" it.

## Mode 2 — `bbox`

Triggers if **any pixel of the bounding box overlaps the ROI.**

### How it works

[detect.py:99-108](../detect.py#L99-L108)

```python
def bbox_overlaps_roi(x1, y1, x2, y2, roi_mask):
    bx1, by1 = max(x1, 0), max(y1, 0)
    bx2, by2 = min(x2, w), min(y2, h)
    if bx1 >= bx2 or by1 >= by2:
        return False
    return bool(roi_mask[by1:by2, bx1:bx2].any())
```

Once at startup we render the ROI polygon into a binary mask the size of
the frame ([detect.py:139-142](../detect.py#L139-L142)) using
`cv2.fillPoly`. Then per detection, we slice the mask under the bbox and
ask "is any pixel set?". This catches every overlap case correctly:

- bbox corner inside ROI ✓
- ROI fully inside bbox ✓
- bbox edge crossing ROI without any vertex inside ✓

### When `bbox` works well

- Webcam at face level (only head/shoulders visible)
- Crowded scenes with partial occlusion
- ROIs defined on the *image* rather than the floor

### When `bbox` over-triggers

A person standing well outside the zone whose **arm** or **bag** crosses
the ROI line will trigger an alert. In production this is usually
mitigated with a coverage threshold — *"alert if at least 20% of the bbox
area is inside the ROI"* — instead of plain "any overlap." That's a small
extension of this approach, not a different one.

## Aggregation

Either mode produces a per-detection boolean. The per-frame loop OR's
those booleans together ([detect.py:145-156](../detect.py#L145-L156)):

```python
person_in_roi = False
for box in boxes:
    ...
    if inside:
        person_in_roi = True
```

So one frame produces one verdict — *"is at least one person inside the
ROI right now?"* — regardless of how many people are visible or which
mode is active.

## How to switch

```bash
python detect.py --source clip.mp4                 # feet (default)
python detect.py --source clip.mp4 --check bbox    # any bbox overlap
```

The active mode is shown in the top-left of the live window
(`check: feet` / `check: bbox`) so you can confirm at a glance.
