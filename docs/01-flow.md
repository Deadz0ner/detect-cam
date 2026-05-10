# Flow

The whole program is one loop wrapped in a setup phase and a cleanup phase.

## Project layout

```
detect.py          ← entry point: argparse + the per-frame loop
config.py          ← shared constants (thresholds, colours)
roi.py             ← ROI building (default + interactive picker) + helpers
checks.py          ← "is this person inside the ROI?" — both modes
drawing.py         ← all visual overlays painted on the frame
```

Each module is small and self-contained; `detect.py` is just the glue.

## Setup (runs once)

1. Parse CLI args ([detect.py](../detect.py) → `parse_args`)
2. Load YOLO weights — first run downloads them
3. Open the video source — webcam, file, or RTSP URL
4. Read the **first frame** so the ROI picker has something to display
5. Build the ROI:
   - Default → axis-aligned rectangle (`build_default_roi` in [roi.py](../roi.py))
   - `--pick-roi` → interactive polygon picker (`pick_roi_interactively` in [roi.py](../roi.py))
6. Precompute helpers for the ROI:
   - `build_roi_aabb` → polygon's bounding rectangle (always)
   - `build_roi_mask` → binary pixel mask (only for non-rectangular polygons)
7. Optionally open a `VideoWriter` if `--save` was passed

## Loop (runs per frame)

For every frame, in order:

1. **Detect** — run YOLO on the frame → list of objects
   ([03-model.md](03-model.md))
2. **Filter** — keep only `person` boxes above the confidence threshold
3. **Check** — is the person inside the ROI?
   - `feet` mode → `feet_point` + `is_inside_roi` ([checks.py](../checks.py))
   - `bbox` mode → `bbox_overlaps_roi` (AABB fast-reject + mask) ([checks.py](../checks.py))
4. **Draw** — `draw_detection` per person, then `draw_roi`
   ([drawing.py](../drawing.py))
5. **Alert** — if anyone is inside the ROI and the 2-second cooldown has
   elapsed, print one line to stdout ([06-alerting.md](06-alerting.md))
6. **Overlay** — `draw_overlay` for the top-left FPS / frame / mode line
7. **Save / show** — write to MP4 if `--save`, display in window unless `--headless`
8. **Read next frame** — loop

## Cleanup (runs once)

- Release the camera/file
- Release the video writer if used
- Close any OpenCV windows

## Visual

```
┌─ Setup ──────────────────────────────────────────────────────────┐
│ args → YOLO → cap → first_frame → roi → roi_aabb → roi_mask?     │
└─────────────────┬────────────────────────────────────────────────┘
                  ▼
┌─ Loop (per frame) ────────────────────────────────────────────────┐
│ detect → filter → check (feet | bbox) → draw → alert → save/show  │
└─────────────────┬─────────────────────────────────────────────────┘
                  ▼ (on EOF or 'q')
┌─ Cleanup ──────────────────────────────────────┐
│ release cap, release writer, close UI windows  │
└────────────────────────────────────────────────┘
```

Each step has its own doc — see [docs/README.md](README.md).
