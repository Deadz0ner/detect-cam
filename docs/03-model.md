# Model I/O

How the YOLO model is called, what it eats, what it returns, and how that
return value becomes "person inside ROI?".

## Loading

In [detect.py](../detect.py) → `main`:

```python
model = YOLO("yolov8n.pt")
```

`yolov8n.pt` is a 6 MB pretrained weights file. First run auto-downloads
it; afterwards it's loaded from disk. Internally, this constructs a
PyTorch neural network and loads the trained parameters.

## Calling the model

```python
results = model(frame, verbose=False)[0]
```

### Input

A single **frame** — a NumPy array of shape `(H, W, 3)`, dtype `uint8`,
channels in **BGR** order (that's just how OpenCV gives them to us).

That's it. No resizing, no normalisation, no tensor conversion needed —
Ultralytics handles all of that internally before passing the data to PyTorch.

### Output

`results` is a `Results` object. The attribute we care about is `.boxes`,
an iterable of `Box` objects. Each `Box` exposes:

| Attribute | Shape | What it is |
|---|---|---|
| `.cls` | (1,) | Class index (e.g. `0` = person, `2` = car) |
| `.conf` | (1,) | Confidence score, 0.0–1.0 |
| `.xyxy` | (1, 4) | Bounding box: `[x1, y1, x2, y2]` in **pixel** coordinates |

Every value is a tensor; we cast to plain Python with `int()` / `float()` /
`.tolist()`.

A typical detection looks like:
```
cls = 0           # person
conf = 0.87       # 87% confident
xyxy = [120, 200, 260, 480]    # top-left → bottom-right of the box
```

## How we turn output into "alert?"

Per detection, inside [detect.py](../detect.py) → `main`:

```
1. cls != PERSON_CLASS_ID  OR  conf < args.conf      →  skip this box
2. read xyxy → cast to ints (x1, y1, x2, y2)
3. branch on --check:
     feet → feet_point(x1,y1,x2,y2) → is_inside_roi(point, roi)
     bbox → bbox_overlaps_roi(x1,y1,x2,y2, roi_aabb, roi_mask)
4. if inside: person_in_roi = True
```

The two check functions live in [checks.py](../checks.py). After the
per-box loop finishes, `person_in_roi` is a single boolean for the whole
frame. That boolean (plus the cooldown timer) is what gates the alert
print.

## Why this design

- **One model call per frame, not per person.** YOLO is single-shot: one
  forward pass produces all detections in the frame. Calling it once per
  person would be wasteful and wrong.
- **No tracking.** We don't link detections across frames. Each frame is
  a fresh question: "is anyone in the ROI right now?"
- **Pluggable check mode.** Both `feet` and `bbox` operate on the same
  bbox; only the `inside` computation differs. The model isn't aware which
  mode is in use.
