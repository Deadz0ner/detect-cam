# Flow

The whole program is one loop wrapped in a setup phase and a cleanup phase.

## Setup (runs once)

1. Parse CLI args ([detect.py:117](../detect.py#L117))
2. Load the YOLO model — first run downloads weights ([detect.py:120](../detect.py#L120))
3. Open the video source — webcam, file, or RTSP URL ([detect.py:121](../detect.py#L121))
4. Read the **first frame** ([detect.py:125](../detect.py#L125))
5. Build the ROI — interactively or from defaults ([detect.py:130](../detect.py#L130))
6. Optionally open a `VideoWriter` if `--save` was passed ([detect.py:132-136](../detect.py#L132-L136))

## Loop (runs per frame)

For every frame, in order:

1. **Detect** — run YOLO on the frame → list of objects
2. **Filter** — keep only `person` boxes above the confidence threshold
3. **Locate feet** — bottom-center of each person box
4. **Check ROI** — is the feet-point inside the polygon?
5. **Draw** — green box (outside) or red box (inside), plus the orange ROI outline and the FPS counter
6. **Alert** — if anyone is inside the ROI and the 2-second cooldown has elapsed, print a line to stdout
7. **Save / show** — write to MP4 if `--save`, display in window unless `--headless`
8. **Read next frame** — loop

## Cleanup (runs once)

- Release the camera/file ([detect.py:190](../detect.py#L190))
- Release the video writer if used ([detect.py:191-192](../detect.py#L191-L192))
- Close any windows ([detect.py:193](../detect.py#L193))

## Visual

```
┌─ Setup ───────────────────────────────┐
│ args → model → cap → first_frame → ROI │
└─────────────────┬──────────────────────┘
                  ▼
┌─ Loop (per frame) ──────────────────────┐
│ detect → filter → feet → check → draw   │
│            → alert → save/show → next   │
└─────────────────┬───────────────────────┘
                  ▼ (on EOF or 'q')
┌─ Cleanup ─────────────────────────────┐
│ release cap, release writer, close UI │
└───────────────────────────────────────┘
```

Each step has its own doc — see [docs/README.md](README.md).
