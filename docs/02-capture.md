# Capture

How frames flow in from the outside world.

## The one line that does it all

```python
cap = cv2.VideoCapture(source)   # detect.py:121
```

OpenCV's `VideoCapture` is overloaded based on what you hand it:

| `source` value | What OpenCV does |
|---|---|
| Integer `0`, `1`, ... | Open camera device at that index (Linux: `/dev/video0`, etc.) |
| String path | Open the video file |
| String URL (`rtsp://...`, `http://...`) | Open the network stream |

`detect.py` accepts any of these via `--source`. If the value is a digit
string it's converted to an int first ([detect.py:118](../detect.py#L118));
otherwise it's passed through as a string.

## Reading a frame

```python
ok, frame = cap.read()   # detect.py:125 (first frame), 185 (loop)
```

- `ok` is `True` while there are still frames; `False` on end-of-file or
  device error.
- `frame` is a NumPy array of shape `(H, W, 3)`, dtype `uint8`, BGR channels.

## Why we read the first frame *before* the loop

We need a frame on hand at startup so the ROI picker can show it as a still
image. Once that's done, the same frame is reused as the first iteration's
input, and `cap.read()` is called at the **end** of each loop iteration to
get the next one ([detect.py:185](../detect.py#L185)).

## Cleanup

```python
cap.release()   # detect.py:190
```

This frees the camera handle / closes the file. Forgetting this can leave
the webcam locked until the process is killed.
