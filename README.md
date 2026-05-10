# detect-cam

A small Python script that watches a video or webcam, finds people with
YOLOv8n, draws a box around each one, and prints an alert when anyone
steps into a defined zone:

```
ALERT: Person in restricted area
```

## Setup

You'll need Python 3.10+ and around 500 MB of disk for dependencies.
A GPU is **not** required — CPU is fine.

```bash
git clone https://github.com/Deadz0ner/detect-cam.git
cd detect-cam

python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The first run auto-downloads the YOLOv8n weights (~6 MB). Everything
after that is offline.

## Run

The quickest way to try it:

```bash
python src/detect.py
```

That opens your default webcam. Press **`q`** in the window to quit.

### Pick a video source

```bash
python src/detect.py                              # default webcam
python src/detect.py --source 1                   # second webcam
python src/detect.py --source clip.mp4            # a video file
python src/detect.py --source rtsp://192.168...   # IP camera
```

`--source` takes a digit (webcam index), a file path, or an RTSP/HTTP
URL. OpenCV figures out the rest.

### Useful flags

```bash
python src/detect.py --pick-roi             # draw your own ROI on the first frame
python src/detect.py --save out.mp4         # record an annotated MP4 to disk
python src/detect.py --conf 0.5             # raise the detection threshold
python src/detect.py --check bbox           # alert on any bbox/ROI overlap (see below)
python src/detect.py --headless             # don't show the window (useful for SSH)
```

### ROI picker controls

When you pass `--pick-roi`, the first frame freezes so you can draw the zone:

| Action | Key / mouse |
|---|---|
| Add a polygon vertex | left-click |
| Confirm | **Enter** (need ≥3 points) |
| Reset and start over | **R** |
| Use the default ROI instead | **C** |
| Abort | **Esc** |

### Check modes

`--check` controls what it means for a person to be "in" the ROI:

- **`feet`** (default) — only the bottom-center of the bounding box is
  tested. Right answer for cameras looking down at a floor.
- **`bbox`** — any pixel of the bounding box that touches the ROI
  triggers an alert. Right answer for close-range scenes (e.g. a laptop
  webcam) where the feet are off-screen.

The currently active mode shows in the top-left of the window.

## Approach

The code lives in `src/` as small modules so each piece reads on its own:

```
src/
├── detect.py     entry point — argparse + the per-frame loop
├── config.py     shared constants
├── roi.py        ROI building (default + interactive picker)
├── checks.py     "is this person inside the ROI?"
└── drawing.py    overlays painted on each frame
```

Each frame goes through one loop:

1. Grab a frame from the source.
2. Run YOLO. Keep only "person" boxes above the confidence threshold.
3. For each person, decide whether they're inside the ROI (using the
   chosen `--check` mode).
4. Draw the box — green if outside the ROI, red if inside — plus the
   orange ROI outline.
5. If anyone is inside, print the alert. Throttled to once every
   2 seconds so it doesn't spam.
6. Show the frame in a window and/or write it to the saved MP4.

The default ROI is a hardcoded rectangle covering the middle-bottom of
the frame. With `--pick-roi`, you draw any polygon.

For a deeper walkthrough of each piece, see [`docs/`](docs/).

## Limitations

- **No tracking.** The same person re-alerts every 2 seconds while they
  stay in the zone. A real system would assign each person an ID
  (ByteTrack / DeepSORT) and alert once on entry.
- **The ROI is hardcoded** (or drawn at startup). It doesn't persist
  across runs and assumes the camera stays put.
- **CPU-only.** Expect ~10–20 FPS on a modern laptop, less on older
  hardware. A GPU would speed it up without code changes.
- **Alerts are stdout-only.** No log file, no webhook, no email.
- **`feet` mode assumes a floor-plane ROI** seen by a camera that
  captures the whole body. Use `--check bbox` for close-range scenes —
  it solves that case but has its own trade-offs
  ([docs/05-detection-check.md](docs/05-detection-check.md)).
