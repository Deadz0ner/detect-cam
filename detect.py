"""Entry point — argparse + the per-frame loop.

Pipeline (matches docs/01-flow.md):
    1. Parse CLI args.
    2. Load YOLOv8n and open the video source.
    3. Read the first frame and build the ROI (default rectangle, or
       interactive polygon picker if --pick-roi was passed).
    4. Precompute the ROI's bounding rectangle (always) and pixel mask
       (only for non-rectangular polygons).
    5. Loop: detect → filter to people → check vs ROI → draw → alert →
       show / save → read next frame.
    6. Cleanup.

The per-step implementations live in separate modules so each file stays
short. See docs/ for the prose explanation of each step.
"""

import argparse
import time
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO

from checks import bbox_overlaps_roi, feet_point, is_inside_roi
from config import (
    ALERT_COOLDOWN_SEC,
    DEFAULT_CONF,
    INSIDE_COLOR,
    OUTSIDE_COLOR,
    PERSON_CLASS_ID,
)
from drawing import draw_detection, draw_overlay, draw_roi
from roi import (
    build_default_roi,
    build_roi_aabb,
    build_roi_mask,
    pick_roi_interactively,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0",
                        help="Video source: '0' for default webcam, or a path to a video file.")
    parser.add_argument("--model", default="yolov8n.pt",
                        help="YOLO weights file (auto-downloaded on first run).")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF,
                        help=f"Confidence threshold for person detection (default {DEFAULT_CONF}).")
    parser.add_argument("--check", default="feet", choices=["feet", "bbox"],
                        help="ROI check mode. 'feet' (default) = bottom-center of "
                             "bbox must be inside the ROI. 'bbox' = any pixel of "
                             "the bounding box overlaps the ROI.")
    parser.add_argument("--pick-roi", action="store_true",
                        help="Click polygon points on the first frame to define the ROI.")
    parser.add_argument("--save", default=None,
                        help="If set, write the annotated stream to this MP4 path.")
    parser.add_argument("--headless", action="store_true",
                        help="Run without showing the live window (useful over SSH).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Webcam indices come in as digit strings ("0", "1"); paths/URLs are
    # passed through to OpenCV as-is. OpenCV figures out the rest.
    source = int(args.source) if args.source.isdigit() else args.source

    # First call to YOLO() auto-downloads weights (~6 MB) if missing.
    model = YOLO(args.model)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source: {args.source}")

    # Read the first frame separately so the ROI picker has something to
    # show. We then reuse this same frame as the loop's first iteration.
    ok, frame = cap.read()
    if not ok:
        raise SystemExit("Could not read first frame from source.")

    h, w = frame.shape[:2]

    # -- Build the ROI and its precomputed helpers ----------------------------
    # `is_rect` records whether the polygon is an axis-aligned rectangle.
    # When True we can skip the pixel mask entirely — the AABB overlap test
    # in checks.py is mathematically exact for rectangles.
    if args.pick_roi:
        roi = pick_roi_interactively(frame)
        is_rect = False
    else:
        roi = build_default_roi(w, h)
        is_rect = True

    roi_aabb = build_roi_aabb(roi)
    roi_mask = None if is_rect else build_roi_mask(roi, (h, w))
    # -------------------------------------------------------------------------

    # Optional MP4 writer for --save.
    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0
        writer = cv2.VideoWriter(args.save, fourcc, fps_in, (w, h))

    last_alert_at = 0.0
    prev_frame_time = time.time()
    frame_idx = 0

    while True:
        # YOLO inference for this frame. verbose=False silences per-frame
        # Ultralytics logs that would otherwise drown out our ALERT lines.
        results = model(frame, verbose=False)[0]

        person_in_roi = False
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            # Keep only people above the confidence threshold.
            if cls != PERSON_CLASS_ID or conf < args.conf:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            # Apply the active check mode.
            if args.check == "feet":
                anchor = feet_point(x1, y1, x2, y2)
                inside = is_inside_roi(anchor, roi)
            else:
                # bbox mode: AABB fast-reject first, mask fallback if needed.
                anchor = None
                inside = bbox_overlaps_roi(x1, y1, x2, y2, roi_aabb, roi_mask)

            if inside:
                person_in_roi = True

            color = INSIDE_COLOR if inside else OUTSIDE_COLOR
            draw_detection(frame, x1, y1, x2, y2, color, f"person {conf:.2f}", anchor)

        # ROI outline goes on top of the per-person boxes so it stays visible.
        draw_roi(frame, roi)

        # Throttled alert — at most one print every ALERT_COOLDOWN_SEC seconds.
        now = time.time()
        if person_in_roi and (now - last_alert_at) >= ALERT_COOLDOWN_SEC:
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{stamp}][frame {frame_idx}] ALERT: Person in restricted area")
            last_alert_at = now

        # Top-left overlay: FPS + frame index + active check mode.
        fps = 1.0 / max(now - prev_frame_time, 1e-6)
        prev_frame_time = now
        draw_overlay(frame, fps, frame_idx, args.check)

        if writer is not None:
            writer.write(frame)

        if not args.headless:
            cv2.imshow("detect-cam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        # Advance to the next frame.
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
