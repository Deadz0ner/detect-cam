# Output

Two output channels for the annotated frame: a live window, and an MP4 on
disk. They're independent — you can do either, both, or neither. Both live
in [detect.py](../src/detect.py) → `main`.

## Live window

```python
if not args.headless:
    cv2.imshow("detect-cam", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
```

`cv2.imshow` opens (or reuses) a window titled `"detect-cam"` and displays
the frame. `cv2.waitKey(1)` is essential — it gives the OS a 1-millisecond
window to paint the GUI and read keyboard input. Without it, the window
would freeze and never update.

`q` exits the loop. The mask `& 0xFF` is the standard way to compare key
codes across platforms.

Skip the window entirely with `--headless`. Useful when:
- Running over SSH with no display
- You only care about saving an MP4 and seeing the alert log
- Squeezing every bit of CPU into detection

## Saved MP4

```python
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0
writer = cv2.VideoWriter(args.save, fourcc, fps_in, (w, h))
...
writer.write(frame)
```

Triggered by `--save out.mp4`. We:

1. Pick the `mp4v` codec.
2. Read the source's FPS so the saved video plays at real speed
   (fall back to 25 fps if the source doesn't report one — common for
   webcams).
3. Open a writer with the same width/height as the source.
4. Write each annotated frame inside the loop.

The output file contains exactly what you'd see on screen, with all the
overlays baked in. Great for review and for screenshots in the README.

## Cleanup

```python
if writer is not None:
    writer.release()
```

Forgetting this leaves the MP4 with no proper trailer, and players will
either refuse to open it or report 0:00 duration. Always release.

## Stdout (the alert log)

The third output, kind of. Alert lines go to stdout — see
[06-alerting.md](06-alerting.md). Pipe them to a file if you want a record:

```bash
python src/detect.py --source clip.mp4 --pick-roi --save out.mp4 | tee alerts.log
```
