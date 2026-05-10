# Docs

Short notes on how each piece of `detect.py` works. Read them in order — each
one builds on the previous.

| # | File | What it covers |
|---|---|---|
| 01 | [flow.md](01-flow.md) | The end-to-end pipeline: setup → loop → cleanup |
| 02 | [capture.md](02-capture.md) | Reading frames from webcam / video / IP camera |
| 03 | [model.md](03-model.md) | What goes into the YOLO model and what comes out |
| 04 | [roi.md](04-roi.md) | Defining the region of interest (default + interactive) |
| 05 | [detection-check.md](05-detection-check.md) | Deciding if a person is inside the ROI |
| 06 | [alerting.md](06-alerting.md) | Printing alerts with cooldown |
| 07 | [drawing.md](07-drawing.md) | Boxes, polygons, and text overlays |
| 08 | [output.md](08-output.md) | Live window + saving an annotated MP4 |
| 09 | [why-feet-check.md](09-why-feet-check.md) | The reasoning behind feet_point — 2D polygon, 3D scene, floor plane |
