# Drawing

Everything drawn on the frame is OpenCV painting on top of a NumPy array
in-place. There's no separate "canvas" — the same `frame` we hand to YOLO
is the one we draw on, then either show or save.

## The four overlays

### 1. Person bounding box

[detect.py:159](../detect.py#L159)

```python
cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
```

`color` flips between green (outside ROI) and red (inside) based on the
detection check. Thickness is 2 pixels.

### 2. Feet dot

[detect.py:160](../detect.py#L160)

```python
cv2.circle(frame, point, 4, color, -1)
```

A small filled dot at the bottom-center of the box, in the same color as
the box. Visual confirmation of *which* point is being polygon-tested.

### 3. Person label

[detect.py:161-162](../detect.py#L161-L162)

```python
cv2.putText(frame, f"person {conf:.2f}", (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
```

`"person 0.87"` above the top-left corner of the box. The
`max(y1 - 8, 12)` keeps the label from going off the top edge.

### 4. ROI polygon outline

[detect.py:164](../detect.py#L164)

```python
cv2.polylines(frame, [roi], isClosed=True, color=ROI_COLOR, thickness=2)
```

Orange outline around the ROI. `isClosed=True` makes it draw the line back
from the last vertex to the first, so the polygon visually closes.

### 5. FPS / frame counter (top-left)

[detect.py:174-175](../detect.py#L174-L175)

```python
cv2.putText(frame, f"FPS: {fps:.1f}  frame: {frame_idx}", ...)
```

Used both for performance debugging and for matching saved video frames to
alert-log lines.

## Color conventions

Defined as constants at the top of the file ([detect.py:20-23](../detect.py#L20-L23)):

| Color | BGR | Used for |
|---|---|---|
| Orange | `(0, 165, 255)` | ROI outline |
| Red | `(0, 0, 255)` | Person inside ROI |
| Green | `(0, 255, 0)` | Person outside ROI |
| White | `(255, 255, 255)` | FPS / frame counter text |

Note: OpenCV uses **BGR**, not RGB — that's why "red" looks like
`(0, 0, 255)` rather than `(255, 0, 0)`.

## Order matters

The ROI is drawn **after** the person boxes ([detect.py:164](../detect.py#L164))
so it sits visually on top of any boxes that overlap it. Last drawn = on
top.
