"""Constants used across the pipeline.

Centralised here so every module can import them without circular deps,
and so a reviewer can find every tunable in one place.
"""

# COCO class index for 'person'. YOLOv8 ships with the standard 80-class
# COCO label set; 'person' is class 0. We filter detections by this index.
PERSON_CLASS_ID = 0

# Default confidence threshold for keeping a detection. Below this we
# discard the box as too uncertain. Overridable via --conf.
DEFAULT_CONF = 0.4

# We don't print the same alert more often than this. Prevents the
# terminal from being flooded while a person stands inside the ROI.
ALERT_COOLDOWN_SEC = 2.0

# OpenCV uses BGR ordering for colours, not RGB. So "red" is (0, 0, 255).
ROI_COLOR = (0, 165, 255)     # orange — drawn around the ROI polygon
INSIDE_COLOR = (0, 0, 255)    # red — person whose check says "inside ROI"
OUTSIDE_COLOR = (0, 255, 0)   # green — person whose check says "outside ROI"
FPS_COLOR = (255, 255, 255)   # white — top-left overlay text
