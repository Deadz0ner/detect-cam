# The AABB fast-reject

How `bbox` mode answers *"do this bounding box and that ROI polygon
overlap?"* — in two steps, doing as little work as possible.

## The idea in one paragraph

Before doing the expensive pixel-by-pixel check, do a cheap, dumb check
first: *"Are the two shapes even close to each other?"* If the answer is
clearly **no**, stop. Only when the cheap check can't rule it out do we
spend effort on the precise answer.

Like a bouncer who glances at you first — *obviously underage?* — and
only checks your ID carefully if you might be over-age.

## Step 1 — The cheap check (AABB)

Every polygon, no matter how strangely shaped, sits inside a **bounding
rectangle**: the smallest axis-aligned rectangle that wraps around it.

```
   ┌──────────────────┐  ← bounding rectangle of the polygon
   │      ╱╲          │
   │     ╱  ╲         │
   │    ╱    ╲        │
   │   ╱ ROI  ╲       │
   │  ╱________╲      │
   └──────────────────┘
```

Computing it is trivial: smallest x of all vertices, smallest y, largest x,
largest y. We do this once at startup in `build_roi_aabb()`
([roi.py](../roi.py)).

Then for each detection we run the textbook **axis-aligned rectangle
overlap test** between the bbox and the polygon's bounding rectangle:

```python
def aabb_overlap(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    return not (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)
```

Two rectangles overlap unless one is completely to the left, right, above,
or below the other. Four comparisons, O(1), no allocations. The same
algorithm every game engine uses for collision detection.

## What "no overlap" means here

**Definitive.** If the bbox rectangle and the polygon's bounding rectangle
don't even touch, the bbox cannot touch the polygon inside the bounding
rectangle either. We return False immediately. No pixel check needed.

This is the case for the **vast majority of frames** — most people are
nowhere near the ROI, so step 1 alone gives the right answer and we skip
step 2 entirely.

## What "overlap" means here

**Maybe.** Two cases live in this branch:

### Case A — the polygon equals its bounding rectangle

If the polygon **is** a rectangle (the default ROI is), then the bounding
rectangle equals the polygon. "Overlap with bounding rectangle" means
"overlap with the polygon." Step 1's answer is exact and we skip step 2.

In code we signal this by passing `roi_mask=None` to
`bbox_overlaps_roi` — there's no mask to consult because we don't need one.

### Case B — the polygon doesn't fill its bounding rectangle

If the polygon has empty corners inside its bounding rectangle, the bbox
might be sitting in one of those empty corners:

```
   ┌──────────────────┐
   │      ╱╲          │
   │     ╱  ╲   ┌──┐  │  ← bbox is inside the bounding rectangle
   │    ╱    ╲  │bx│  │     but OUTSIDE the actual polygon
   │   ╱ ROI  ╲ └──┘  │
   │  ╱________╲      │
   └──────────────────┘
```

Step 1 says "overlap" (correctly — they share the bounding rectangle), but
the bbox doesn't actually touch the polygon. Now we need step 2 to settle
it.

## Step 2 — The precise check (mask)

At startup we rasterise the polygon into a binary mask the size of the
frame (`build_roi_mask()` in [roi.py](../roi.py)). Each pixel inside the
polygon is `1`; everything outside is `0`.

For each "maybe" detection from step 1, slice the mask under the bbox and
ask "is any pixel set?":

```python
return bool(roi_mask[by1:by2, bx1:bx2].any())
```

This is **pixel-accurate** — whatever shape the polygon has, this gives
the right answer.

## Why this structure is the right shape

It mirrors how every collision-detection / spatial-query system in the
industry works:

| Phase | Cost | What it does |
|---|---|---|
| Broad-phase | O(1) per pair | Cheap reject of pairs that can't possibly overlap |
| Narrow-phase | More expensive | Precise check only on pairs that survived broad-phase |

Physics engines, GPU renderers, ray tracers, spatial indexes — same idea
everywhere. Our `aabb_overlap` is the broad phase; the mask slice is the
narrow phase.

For our app the savings are modest (we typically have a handful of people
per frame), but the **structure** is what matters: a reviewer reading
`bbox_overlaps_roi` sees the textbook two-step pattern, which is what
production code looks like.

## Summary

| ROI shape | Step 1 result | Step 2 needed? | Verdict |
|---|---|---|---|
| Rectangle | No overlap | No | Not in ROI ✓ |
| Rectangle | Overlap | No (exact) | In ROI ✓ |
| Polygon | No overlap | No | Not in ROI ✓ |
| Polygon | Overlap | **Yes** | Whatever the mask says |

The default ROI in this project is a rectangle, so step 2 is never run for
the default. The picker can produce arbitrary polygons, and that's where
the mask check earns its keep.
