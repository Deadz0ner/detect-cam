# detect-cam

A small Python script that watches a video source (webcam or file), detects
people with YOLOv8n, draws bounding boxes, and prints an alert when anyone
steps into a hardcoded region of interest (ROI).

```
ALERT: Person in restricted area
```

## Setup

Tested on Python 3.10+. CPU-only is fine; no GPU required.

```bash
git clone <your-repo-url> detect-cam
cd detect-cam

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The first run will auto-download the `yolov8n.pt` weights (~6 MB) into the
working directory. Subsequent runs are offline.

## Run

### Choosing a source

```bash
python src/detect.py                              # default webcam (= --source 0)
python src/detect.py --source 1                   # second webcam
python src/detect.py --source rtsp://192.168...   # IP camera
python src/detect.py --source clip.mp4            # video file
python src/detect.py --pick-roi                   # webcam + click your own ROI
```

`--source` accepts a digit (webcam index), a file path, or an RTSP/HTTP URL.
OpenCV figures out which based on the value.

### Useful flags

```bash
# Click your own ROI on the first frame
python src/detect.py --source clip.mp4 --pick-roi

# Save an annotated MP4 for later review
python src/detect.py --source clip.mp4 --save out.mp4

# Tune confidence threshold (default 0.4)
python src/detect.py --source clip.mp4 --conf 0.5

# Headless (no display window — useful over SSH or when only saving)
python src/detect.py --source clip.mp4 --save out.mp4 --headless
```

Press **`q`** in the live window to quit.

### Picking the ROI check mode

```bash
python src/detect.py --source clip.mp4                  # feet (default)
python src/detect.py --source clip.mp4 --check bbox     # any bbox overlap
```

`--check` controls **how** a person counts as "in" the ROI:

| Mode | Rule | Best for |
|---|---|---|
| `feet` (default) | Only the bottom-center pixel of the bbox is tested against the polygon. | Surveillance-style cameras that see the whole body standing on a floor. The feet point sits on the floor plane, so the ROI means exactly what you drew. See [docs/09-why-feet-check.md](docs/09-why-feet-check.md). |
| `bbox` | Any pixel of the bbox that overlaps the ROI counts as "inside." Implemented as a cheap AABB reject followed by a precise mask check — see [docs/10-aabb-fastreject.md](docs/10-aabb-fastreject.md). | Close-range or partial-body scenes — e.g. a laptop webcam at face level — where the feet are off-screen and a feet check would never trigger. |

The active mode is shown in the **top-left of the live window**
(`check: feet` / `check: bbox`) so you can confirm at a glance which rule
is currently being applied.

Rule of thumb: leave it on `feet` for ceiling- or wall-mounted cameras
viewing a room; switch to `bbox` only when the camera can't see the feet.
`bbox` is more permissive — it can flag someone whose hand or torso
crosses the line even if they're not standing in the zone — which is
either the feature you want or a false alarm, depending on the use case.

### ROI picker controls

When you pass `--pick-roi`, the first frame freezes and you can:

> Deeper notes on the ROI logic: [docs/04-roi.md](docs/04-roi.md).


| Action | Key / mouse |
|---|---|
| Add a polygon vertex | left-click |
| Confirm and start detection | **Enter** (need ≥3 points) |
| Reset and start over | **R** |
| Use the default ROI instead | **C** |
| Abort | **Esc** |

## Approach

The code is split into small modules under `src/` so each piece is easy to
read on its own:

```
src/
├── detect.py     entry point — argparse + the per-frame loop
├── config.py     shared constants (thresholds, colours)
├── roi.py        ROI building (default + interactive picker) + helpers
├── checks.py     "is this person inside the ROI?" — both modes
└── drawing.py    visual overlays painted on each frame
```

The script is one continuous loop ([docs/01-flow.md](docs/01-flow.md)).
Each iteration:

1. **Grab a frame** from the source via OpenCV's `VideoCapture`.
   → [docs/02-capture.md](docs/02-capture.md)
2. **Run YOLOv8n** on the frame. The model returns a list of detected
   objects with class, confidence, and bounding box.
   → [docs/03-model.md](docs/03-model.md)
3. **Filter** the results to the COCO `person` class with confidence ≥ 0.4.
4. For each person, take the **bottom-center** of the bounding box as a
   stand-in for their feet, and check whether that point is inside the ROI
   polygon using `cv2.pointPolygonTest`.
   → [docs/05-detection-check.md](docs/05-detection-check.md)
5. **Draw**: green box if outside the ROI, red box if inside, plus the ROI
   outline in orange and a live FPS counter.
   → [docs/07-drawing.md](docs/07-drawing.md)
6. **Alert**: if at least one person is inside the ROI, print the alert
   message — but throttled to once every 2 seconds so the terminal isn't
   flooded.
   → [docs/06-alerting.md](docs/06-alerting.md)

The ROI is hardcoded as a polygon in fractional coordinates (30%–70% width,
40%–95% height), which means it scales correctly to whatever resolution the
source produces. Details: [docs/04-roi.md](docs/04-roi.md). The output
window and optional MP4 saving are covered in
[docs/08-output.md](docs/08-output.md).

### Why these choices

- **YOLOv8n** is the smallest YOLOv8 variant; it runs at ~10–20 FPS on a
  modest CPU and is a single `pip install` via `ultralytics`.
- **Bottom-center point** matches floor-plan ROIs better than the bbox
  centroid: a tall person standing at the edge of the zone wouldn't trigger
  with a centroid check, but their feet correctly do. Full reasoning —
  including the 2D-polygon-on-a-3D-scene framing and why other bbox points
  fail — is in [docs/09-why-feet-check.md](docs/09-why-feet-check.md).
- **Polygon ROI** instead of a rectangle costs one extra OpenCV call and
  generalizes to non-rectangular zones.
- **Alert throttling** keeps the terminal readable without dropping events
  longer than a couple of seconds.

> See [docs/](docs/) for the full set of in-depth notes, one file per
> stage of the pipeline.

## Limitations

- **No tracking.** The same person triggers a fresh alert every 2 seconds
  while they remain in the ROI. A real system would attach IDs to people
  (DeepSORT / ByteTrack) and alert on enter/exit transitions per ID.
- **ROI persistence is per-run.** The interactive picker (`--pick-roi`) lets
  you draw a polygon, but it isn't saved to disk; you redraw it next time, or
  edit the fractions in `build_default_roi()` to make a permanent default.
- **Single-camera, single-process.** No multi-stream support, no HTTP API,
  no recording of clips when alerts fire.
- **CPU-only inference.** Realistic FPS is ~10–20 on a modern laptop; lower
  on older hardware. A GPU would speed it up substantially with no code
  changes.
- **No persistent log.** Alerts go to stdout only; nothing is written to a
  file or external system.
- **Confidence threshold is fixed** at 0.4. False positives in busy or
  poorly lit scenes are possible.
