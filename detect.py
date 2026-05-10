"""Basic AI deployment pipeline.

Watches a video or webcam, detects people with YOLOv8n, draws bounding
boxes, and prints an alert when a person enters a hardcoded restricted
zone.
"""

import argparse
import time
from datetime import datetime

import cv2
from ultralytics import YOLO


PERSON_CLASS_ID = 0       # COCO class index for 'person'
CONF_THRESHOLD = 0.4
ALERT_COOLDOWN_SEC = 2.0
# ROI as (x1, y1, x2, y2) fractions of the frame — middle-bottom area.
ROI_FRACTIONS = (0.30, 0.40, 0.70, 0.95)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0",
                        help="'0' for default webcam, or a video file path / URL.")
    parser.add_argument("--save", default=None,
                        help="Optional path to write the annotated video (MP4).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = int(args.source) if args.source.isdigit() else args.source

    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source: {args.source}")

    ok, frame = cap.read()
    if not ok:
        raise SystemExit("Could not read first frame from source.")

    h, w = frame.shape[:2]
    rx1 = int(ROI_FRACTIONS[0] * w)
    ry1 = int(ROI_FRACTIONS[1] * h)
    rx2 = int(ROI_FRACTIONS[2] * w)
    ry2 = int(ROI_FRACTIONS[3] * h)

    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0
        writer = cv2.VideoWriter(args.save, fourcc, fps_in, (w, h))

    last_alert_at = 0.0

    while True:
        results = model(frame, verbose=False)[0]

        person_in_roi = False
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls != PERSON_CLASS_ID or conf < CONF_THRESHOLD:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            # AABB overlap test: bbox vs ROI rectangle. Four comparisons.
            # Two axis-aligned rectangles overlap UNLESS one is entirely
            # to the left, right, above, or below the other.
            inside = not (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)
            if inside:
                person_in_roi = True

            color = (0, 0, 255) if inside else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Draw the ROI outline (orange).
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 165, 255), 2)

        # Throttled alert.
        now = time.time()
        if person_in_roi and (now - last_alert_at) >= ALERT_COOLDOWN_SEC:
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{stamp}] ALERT: Person in restricted area")
            last_alert_at = now

        if writer is not None:
            writer.write(frame)

        cv2.imshow("detect-cam", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        ok, frame = cap.read()
        if not ok:
            break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
