# detect-cam

A basic AI deployment pipeline. Watches a video or webcam, detects
people with YOLOv8n, draws bounding boxes, and prints an alert when a
person enters a hardcoded restricted zone:

```
ALERT: Person in restricted area
```

> **Disclaimer.** This branch is the deliberately minimal version of the
> project. It does what the assignment asks — nothing more — to keep
> the code simple, readable, and free of over-engineering. A richer
> version with extra features lives on the
> [`extended`](https://github.com/Deadz0ner/detect-cam/tree/extended)
> branch. See the bottom of this README for the full list.

## Setup

Python 3.10+, CPU is fine — no GPU needed.

```bash
git clone https://github.com/Deadz0ner/detect-cam.git
cd detect-cam

python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The first run auto-downloads the YOLOv8n weights (~6 MB).

## Run

```bash
python detect.py                      # default webcam
python detect.py --source clip.mp4    # a video file
python detect.py --save out.mp4       # also write annotated video to disk
```

Press **`q`** in the window to quit.

## Approach

A single `detect.py` runs one frame loop:

1. Grab a frame from the source (webcam or video file).
2. Run YOLOv8n. Keep "person" detections above confidence 0.4.
3. For each person, take the bottom-center of the bounding box as their
   feet position.
4. The ROI is a hardcoded rectangle covering the middle-bottom of the
   frame. Check if the feet point sits inside it with four
   comparisons (`rx1 <= cx <= rx2 and ry1 <= cy <= ry2`).
5. Draw the box — green if outside the ROI, red if inside — plus the
   orange ROI outline.
6. If anyone is inside the ROI, print the alert. Throttled to once
   every 2 seconds so the terminal stays readable.

## Limitations

- **No tracking.** Each person re-alerts every 2 seconds while they
  stay in the zone. Real systems use a tracker (ByteTrack / DeepSORT)
  so each person fires once on entry.
- **ROI is hardcoded** as a rectangle covering the middle-bottom of the
  frame. Change `ROI_FRACTIONS` in `detect.py` to move it.
- **CPU-only.** Expect ~10–20 FPS on a modern laptop. A GPU speeds it
  up without code changes.
- **Alerts go to stdout only.** No log file, no webhook, no email.
- **Feet-point assumes a floor-plane ROI.** For close-range cameras
  (laptop webcam) the bottom of the bbox sits at the chest, not the
  feet, so the check can miss someone who is clearly "in" the zone.

---

## See also: the `extended` branch

**For the full version with additional features, switch to the
[`extended`](https://github.com/Deadz0ner/detect-cam/tree/extended)
branch.**

```bash
git checkout extended
```

It keeps everything here and adds:

- **Interactive ROI picker** (`--pick-roi`) — click polygon vertices on
  the first frame instead of using the hardcoded rectangle.
- **Two ROI check modes** (`--check feet | bbox`) — `feet` for
  surveillance cameras, `bbox` for close-range scenes where the feet
  aren't visible in frame.
- **AABB fast-reject + mask check** — broad-phase / narrow-phase
  polygon overlap detection, the textbook pattern from production
  collision-detection systems.
- **Confidence flag** (`--conf`) to tune the detection threshold.
- **Headless flag** (`--headless`) for SSH or no-display runs.
- **Modular structure** under `src/` (config, roi, checks, drawing,
  detect) for cleaner separation of concerns.
- **Full `docs/` folder** — 10 in-depth markdown files covering each
  stage of the pipeline, the design decisions, and the AABB
  optimisation in detail.
