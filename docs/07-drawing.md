# Drawing

Everything drawn on the frame is OpenCV painting on top of a NumPy array
in place. There's no separate canvas — the same `frame` we hand to YOLO is
the one we draw on, then either show or save. All drawing helpers live in
[drawing.py](../drawing.py).

## The four overlays

### 1. Bounding box + 2. Feet dot + 3. Label

All three are produced by `draw_detection` ([drawing.py](../drawing.py)),
called once per person per frame:

```python
cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
if anchor_point is not None:
    cv2.circle(frame, anchor_point, 4, color, -1)
cv2.putText(frame, label, (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
```

- The **rectangle** colour flips between green (outside ROI) and red (inside).
- The **dot** is the anchor point being tested. In `feet` mode it's the
  feet-point; in `bbox` mode `anchor_point` is `None` and no dot is drawn.
- The **label** is `"person 0.87"` above the top-left corner. The
  `max(y1 - 8, 12)` keeps it from going off the top edge.

### 4. ROI polygon outline

`draw_roi` ([drawing.py](../drawing.py)):

```python
cv2.polylines(frame, [roi], isClosed=True, color=ROI_COLOR, thickness=2)
```

Orange outline around the ROI. `isClosed=True` draws the line back from
the last vertex to the first, so the polygon visually closes.

### 5. FPS / frame / mode counter (top-left)

`draw_overlay` ([drawing.py](../drawing.py)):

```python
cv2.putText(frame, f"FPS: {fps:.1f}  frame: {frame_idx}  check: {check_mode}", ...)
```

Three uses: performance debugging, matching saved-video frames to alert
log lines, and confirming at a glance which `--check` mode is active.

## Colour conventions

Defined as constants in [config.py](../config.py):

| Colour | BGR | Used for |
|---|---|---|
| Orange | `(0, 165, 255)` | ROI outline |
| Red | `(0, 0, 255)` | Person inside ROI |
| Green | `(0, 255, 0)` | Person outside ROI |
| White | `(255, 255, 255)` | FPS / frame / mode text |

Note: OpenCV uses **BGR**, not RGB — that's why "red" looks like
`(0, 0, 255)` rather than `(255, 0, 0)`.

## Order matters

In the main loop, `draw_roi` is called **after** all the `draw_detection`
calls for the frame, so the ROI outline sits visually on top of any
person boxes that overlap it. Last drawn = on top.
