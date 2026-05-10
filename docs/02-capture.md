# Capture

How frames flow in from the outside world. All of this lives in
[detect.py](../src/detect.py) → `main` — capture is simple enough that it
didn't justify its own module.

## The one line that does it all

```python
cap = cv2.VideoCapture(source)
```

OpenCV's `VideoCapture` is overloaded based on what you hand it:

| `source` value | What OpenCV does |
|---|---|
| Integer `0`, `1`, ... | Open camera device at that index (Linux: `/dev/video0`, etc.) |
| String path | Open the video file |
| String URL (`rtsp://...`, `http://...`) | Open the network stream |

`detect.py` accepts any of these via `--source`. If the value is a digit
string it's converted to an int first, otherwise it's passed through.

## Reading a frame

```python
ok, frame = cap.read()
```

- `ok` is `True` while there are still frames; `False` on end-of-file or
  device error.
- `frame` is a NumPy array of shape `(H, W, 3)`, dtype `uint8`, BGR channels.

## Why we read the first frame *before* the loop

We need a frame on hand at startup so the ROI picker can show it as a still
image. Once that's done, the same frame is reused as the loop's first
iteration's input, and `cap.read()` is called at the **end** of each
iteration to fetch the next one.

## Cleanup

```python
cap.release()
```

Run after the loop exits. Frees the camera handle / closes the file.
Forgetting this can leave the webcam locked until the process is killed.
