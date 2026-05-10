# Why feet, and not anything else?

A walk-through of the reasoning behind `feet_point` in
[checks.py](../src/checks.py). Captures the questions asked, the mental model
we landed on, and what the approach can and can't do.

## The question

Why use the bottom-center of the bbox to decide if a person is "in" the ROI?
Why not the center, the top, or some average?

## Mental model

The ROI is a polygon **drawn on the 2D image**. The scene it represents is
**3D**. The camera flattens 3D → 2D, which throws away depth. So a 2D
polygon by itself does **not** define a 3D region — there's no way to.

The only way the drawn polygon gets an unambiguous meaning in the world is
to pin it to a known surface. The natural choice is the **floor plane**:

> The ROI is "this patch of floor."

That's the only interpretation we can make without camera calibration or
depth data.

## Consequence: a person is a 3D vertical object

Only one part of a standing person actually touches the floor — the feet.
Everything else (torso, head) is above the floor and gets projected
**upward** in the image, away from where the person is actually standing.

So the question "is the person standing inside the restricted area?"
becomes:

> Is the pixel where their feet meet the floor inside the polygon?

That pixel is what `feet_point` returns: bottom-center of the bbox.

## Why the alternatives fail

**Bbox center (centroid).** Sits roughly at the waist. Its offset from the
feet depends on:

- **Apparent height in pixels** — a person close to the camera has a tall
  bbox; the center is far above the feet. The same person far away has a
  short bbox; the center is close to the feet. Same person, different
  distance → different "where they are."
- **Pose** — standing: center near waist. Sitting: chest. Crouching: head.
  The centroid's relationship to "where they're standing" is unstable.

**Bbox top (head).** Worst case — projected the furthest from the floor.

**Bbox bottom-center (feet_point).** Always at floor level (or very close)
regardless of pose, height, or distance. The one stable anchor.

## The deeper "why" — what a 2D polygon really is in 3D

When you click polygon points on the image, you are **not** defining a 3D
region. You are defining a **bundle of rays** going out from the camera
through those pixels. That bundle is shaped like a **pyramid** expanding
into the scene.

The pyramid only becomes a definite 2D shape when it **intersects a
plane**. Different planes → different shapes:

- Intersect the **floor** → the patch of floor you intended ✓
- Intersect a plane at **waist height** → a different, shifted patch
- Intersect a plane at **head height** → yet another, more shifted patch

So when you test "is this pixel inside the polygon?", you're really
asking: "does the ray from this pixel pass through the pyramid?" That's
true at *any* height, not just floor height.

A pixel "inside" the polygon could correspond to:

- a person's feet on the floor inside the restricted zone, **or**
- a person's head, where their feet are actually outside the zone — their
  head ray just happens to pass through the pyramid thanks to perspective.

**Feet_point cuts through this ambiguity** by always sampling on the floor
plane — the one plane where the polygon means what you drew.

## What this means in practice

It does **not** matter where the rest of the body is. If the feet are in
the polygon, the person is in the restricted area. They can lean, reach,
or extend their body outside the ROI — that's irrelevant. The floor
contact is what defines "where the person is."

## The polygon test

[checks.py](../src/checks.py) → `is_inside_roi`

```python
def is_inside_roi(point, roi):
    return cv2.pointPolygonTest(roi, point, measureDist=False) >= 0
```

`cv2.pointPolygonTest` with `measureDist=False` returns:

- `+1` → point is inside
- `0` → point is on an edge
- `-1` → point is outside

`>= 0` treats "inside or on the boundary" as a hit.

## Limitations of feet_point

The approach is right for this assignment but breaks in these cases:

- **Person partially off-screen at the bottom** — the bbox bottom clamps
  to the frame edge, not the actual feet. The "feet point" sits at the
  edge of the frame instead of where the feet really are.
- **Person lying down** — the bbox bottom is no longer near the feet; it's
  wherever the body ends.
- **Heavy occlusion of the lower body** — bbox cuts off above the feet,
  so the "feet point" is actually somewhere on the torso.
- **Uncalibrated camera** — we assume the polygon represents a floor
  region, but we never actually compute floor coordinates. If the camera
  moves, the polygon has to be redrawn.

For more robust deployments you'd use a homography to map feet pixels to
real floor coordinates, or pose keypoints (ankles) instead of a bbox
heuristic.
