# Model I/O

How the YOLO model is called, what it eats, what it returns, and how that
return value becomes "person inside ROI?".

## Loading

```python
model = YOLO("yolov8n.pt")   # detect.py:120
```

`yolov8n.pt` is a 6 MB pretrained weights file. First run auto-downloads it;
afterwards it's loaded from disk. Internally, this constructs a PyTorch
neural network and loads the trained parameters.

## Calling the model

```python
results = model(frame, verbose=False)[0]   # detect.py:143
```

### Input

A single **frame** — a NumPy array of shape `(H, W, 3)`, dtype `uint8`,
channels in **BGR** order (that's just how OpenCV gives them to us).

That's it. No resizing, no normalization, no tensor conversion needed —
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

Per detection ([detect.py:146-156](../detect.py#L146-L156)):

```
1. cls != 0  OR  conf < threshold        →  skip this box
2. read xyxy → cast to ints (x1, y1, x2, y2)
3. feet_point = ((x1 + x2) // 2, y2)     → bottom-center
4. inside = cv2.pointPolygonTest(roi, feet_point, False) >= 0
5. if inside: person_in_roi = True
```

After the per-box loop finishes, `person_in_roi` is a single boolean for the
whole frame. That single boolean (plus the cooldown timer) is what gates the
alert print.

## Why this design

- **One model call per frame, not per person.** YOLO is single-shot: one
  forward pass produces all detections in the frame. Calling it once per
  person would be wasteful and wrong.
- **No tracking.** We don't link detections across frames. Each frame is a
  fresh question: "is anyone standing in the ROI right now?"
- **Bottom-center for the feet.** The bbox center can sit above the ROI
  while the person is clearly inside it (tall person at the edge of the
  zone). Using the bottom of the box gets this right.
