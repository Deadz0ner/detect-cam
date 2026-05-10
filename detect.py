"""Person detection with ROI alerting.

Reads frames from a webcam or video file, detects people with YOLOv8n,
draws bounding boxes, and prints an alert when a person enters a
region of interest (ROI).
"""

import argparse
import time
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO


PERSON_CLASS_ID = 0  # COCO 'person'
DEFAULT_CONF = 0.4
ALERT_COOLDOWN_SEC = 2.0
ROI_COLOR = (0, 165, 255)        # orange
INSIDE_COLOR = (0, 0, 255)       # red
OUTSIDE_COLOR = (0, 255, 0)      # green
FPS_COLOR = (255, 255, 255)      # white


def build_default_roi(frame_w: int, frame_h: int) -> np.ndarray:
    """Fallback polygon ROI as fractions of the frame."""
    fractions = np.array([
        [0.30, 0.40],
        [0.70, 0.40],
        [0.70, 0.95],
        [0.30, 0.95],
    ])
    return (fractions * np.array([frame_w, frame_h])).astype(np.int32)


def pick_roi_interactively(first_frame: np.ndarray) -> np.ndarray:
    """Let the user click polygon points on the first frame.

    Controls: left-click to add a point, ENTER to confirm (>=3 points),
    R to reset, C to fall back to the default ROI, ESC to abort.
    """
    points: list[tuple[int, int]] = []
    window = "Pick ROI: click points, ENTER=confirm, R=reset, C=default, ESC=abort"

    def redraw() -> np.ndarray:
        canvas = first_frame.copy()
        for i, p in enumerate(points):
            cv2.circle(canvas, p, 5, ROI_COLOR, -1)
            if i > 0:
                cv2.line(canvas, points[i - 1], p, ROI_COLOR, 2)
        if len(points) >= 3:
            cv2.line(canvas, points[-1], points[0], ROI_COLOR, 1)
        cv2.putText(
            canvas,
            f"points: {len(points)}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            FPS_COLOR,
            2,
        )
        return canvas

    def on_mouse(event: int, x: int, y: int, flags: int, param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        cv2.imshow(window, redraw())
        key = cv2.waitKey(20) & 0xFF
        if key == 13 and len(points) >= 3:        # ENTER
            break
        if key == ord("r"):
            points.clear()
        elif key == ord("c"):
            cv2.destroyWindow(window)
            return build_default_roi(first_frame.shape[1], first_frame.shape[0])
        elif key == 27:                           # ESC
            cv2.destroyWindow(window)
            raise SystemExit("ROI picker aborted.")

    cv2.destroyWindow(window)
    return np.array(points, dtype=np.int32)


def feet_point(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    """Bottom-center of the bounding box — a stand-in for where the person stands."""
    return ((x1 + x2) // 2, y2)


def is_inside_roi(point: tuple[int, int], roi: np.ndarray) -> bool:
    return cv2.pointPolygonTest(roi, point, measureDist=False) >= 0


def bbox_overlaps_roi(
    x1: int, y1: int, x2: int, y2: int, roi_mask: np.ndarray
) -> bool:
    """True if any pixel of the bbox region overlaps the filled ROI mask."""
    h, w = roi_mask.shape
    bx1, by1 = max(x1, 0), max(y1, 0)
    bx2, by2 = min(x2, w), min(y2, h)
    if bx1 >= bx2 or by1 >= by2:
        return False
    return bool(roi_mask[by1:by2, bx1:bx2].any())


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
    source = int(args.source) if args.source.isdigit() else args.source

    model = YOLO(args.model)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source: {args.source}")

    ok, frame = cap.read()
    if not ok:
        raise SystemExit("Could not read first frame from source.")

    h, w = frame.shape[:2]
    roi = pick_roi_interactively(frame) if args.pick_roi else build_default_roi(w, h)

    roi_mask: np.ndarray | None = None
    if args.check == "bbox":
        roi_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(roi_mask, [roi], 1)

    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0
        writer = cv2.VideoWriter(args.save, fourcc, fps_in, (w, h))

    last_alert_at = 0.0
    prev_frame_time = time.time()
    frame_idx = 0

    while True:
        results = model(frame, verbose=False)[0]

        person_in_roi = False
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls != PERSON_CLASS_ID or conf < args.conf:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            if args.check == "feet":
                point = feet_point(x1, y1, x2, y2)
                inside = is_inside_roi(point, roi)
            else:
                point = None
                inside = bbox_overlaps_roi(x1, y1, x2, y2, roi_mask)
            if inside:
                person_in_roi = True

            color = INSIDE_COLOR if inside else OUTSIDE_COLOR
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            if point is not None:
                cv2.circle(frame, point, 4, color, -1)
            cv2.putText(frame, f"person {conf:.2f}", (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        cv2.polylines(frame, [roi], isClosed=True, color=ROI_COLOR, thickness=2)

        now = time.time()
        if person_in_roi and (now - last_alert_at) >= ALERT_COOLDOWN_SEC:
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{stamp}][frame {frame_idx}] ALERT: Person in restricted area")
            last_alert_at = now

        fps = 1.0 / max(now - prev_frame_time, 1e-6)
        prev_frame_time = now
        cv2.putText(frame, f"FPS: {fps:.1f}  frame: {frame_idx}  check: {args.check}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, FPS_COLOR, 2)

        if writer is not None:
            writer.write(frame)

        if not args.headless:
            cv2.imshow("detect-cam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

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
