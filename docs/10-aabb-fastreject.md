# How `bbox` mode checks for overlap

A plain-English walkthrough of the logic in `bbox_overlaps_roi`
([checks.py](../src/checks.py)).

## The question we're answering

> *"Does this person (rectangle) touch the ROI (any shape — triangle,
> rectangle, L-shape, whatever) at all?"*

The person's bounding box is always a rectangle. The ROI can be any shape
with 3+ corners. We want a True/False answer, and we want it cheap.

## The trick: prepare once, check many

We're going to do **two things at startup** (once), so the actual
per-person check becomes simple.

### Setup A — Find the polygon's "wrapper rectangle"

Pretend the polygon is a cardboard cutout on the floor. Walk around it and
find the smallest rectangle you can draw that completely contains it.
That's the **bounding rectangle**.

```
   ┌──────────────────┐  ← wrapper rectangle
   │      ╱╲          │
   │     ╱  ╲         │
   │    ╱    ╲        │
   │   ╱ ROI  ╲       │
   │  ╱________╲      │
   └──────────────────┘
```

To compute it: look at all the polygon's vertices. Smallest x of any
vertex = left edge. Largest x = right edge. Same for y → top and bottom.
Four numbers, done. That's `build_roi_aabb()` in
[roi.py](../src/roi.py).

### Setup B — Paint the polygon onto a "stencil"

Imagine a black sheet of paper the same size as your video. Take a paint
roller and fill in **only the inside of the polygon** with white. Every
pixel inside the polygon becomes `1` (white), every pixel outside stays
`0` (black). That sheet is the **mask**.

```
Polygon:                   Mask:
┌────────────┐             ┌────────────┐
│   ╱╲       │             │ . . . . . .│
│  ╱  ╲      │             │ . . 1 . . .│   ← 1 = inside polygon
│ ╱    ╲     │             │ . 1 1 1 . .│
│╱  ROI ╲    │             │ 1 1 1 1 1 .│   ← 0 = outside polygon
└────────────┘             └────────────┘
```

We build it once at startup with `build_roi_mask()` in
[roi.py](../src/roi.py), and keep it around for the whole run.

> The mask is skipped entirely if the ROI is itself a rectangle — see the
> shortcut described below.

## The actual per-person check

A person walks in, YOLO gives us their bbox `(x1, y1, x2, y2)`. We do this:

### Step 1 — The cheap check ("are they even close?")

Compare two rectangles: the person's **bbox** and the **wrapper
rectangle** from setup A.

We ask: *"Are these two rectangles fully apart from each other?"* That's
four simple comparisons:

- Is the bbox entirely to the **left** of the wrapper? (`bbox.x2 < wrapper.x1`)
- Is the bbox entirely to the **right** of it?
- Is the bbox entirely **above** it?
- Is the bbox entirely **below** it?

If **any** of those is true → they don't touch. The person can't possibly
be inside the polygon. Return False immediately.

If **all four are false** → they overlap somehow. Continue to step 2.

```python
def aabb_overlap(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    return not (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)
```

This is the textbook axis-aligned rectangle overlap test. Four
comparisons, O(1), no allocations.

### Step 2 — The precise check ("are they really overlapping?")

The wrapper rectangle is **loose** — it includes empty space around the
polygon's curves and corners. So step 1 saying "they touch" doesn't yet
mean the bbox actually touches the polygon. It might be sitting in one of
those empty corners:

```
┌──────────────────┐
│   ╱╲             │
│  ╱  ╲     ┌──┐   │  ← bbox is inside the WRAPPER
│ ╱    ╲    │bx│   │     but OUTSIDE the polygon
│╱ ROI  ╲   └──┘   │
└──────────────────┘
```

So we go to the **stencil** (the mask from setup B) and look at just the
rectangle of the stencil underneath the bbox:

```python
roi_mask[by1:by2, bx1:bx2]
```

This pulls out a small rectangle of pixels from the stencil — exactly the
area under the bbox. Now we ask one simple question:

> *"Is there at least one white (1) pixel in this little rectangle?"*

That's `.any()` in NumPy. It scans the rectangle and returns True if any
value is non-zero.

- If yes → the bbox sits over **at least one painted pixel of the polygon**
  → they really overlap → return True.
- If no → it's sitting over only black pixels → the bbox is in an empty
  corner of the wrapper → return False.

## The intuition

The mask is a **pre-painted answer key**. You don't have to do polygon
math at runtime — you painted the polygon once at startup, so checking
"is pixel P inside the polygon?" becomes "what colour is pixel P in the
answer key?" — which is instant.

The bbox is just a rectangle of pixels. Asking "does the bbox overlap the
polygon?" becomes "is any pixel under the bbox painted white in the
answer key?" — which is what `.any()` answers.

## The rectangular-ROI shortcut

If the ROI is itself an axis-aligned rectangle (the default `--pick-roi`
isn't passed) then the wrapper rectangle **equals** the polygon. There
are no empty corners. Step 1's answer is already exact.

In code we signal this by passing `roi_mask=None` to `bbox_overlaps_roi`.
When step 1 says "overlap", we return True without even looking at the
mask (because there isn't one to look at).

This saves both the memory of the mask and the cost of the slice — and
it falls out of the same code, no special-casing.

## Summary table

| ROI shape | Step 1 result | Step 2 needed? | Verdict |
|---|---|---|---|
| Rectangle | No overlap | No | Not in ROI ✓ |
| Rectangle | Overlap | No (exact) | In ROI ✓ |
| Polygon | No overlap | No | Not in ROI ✓ |
| Polygon | Overlap | **Yes** | Whatever the mask says |

The default ROI in this project is a rectangle, so step 2 is never run
for the default. The interactive picker can produce arbitrary polygons,
and that's where the mask check earns its keep.

## Why this structure is the right shape

This pattern — a cheap reject filter followed by a precise check only when
the filter can't rule things out — is how every collision-detection /
spatial-query system in the industry works:

| Phase | Cost | What it does |
|---|---|---|
| Broad-phase | O(1) per pair | Cheap reject of pairs that can't possibly overlap |
| Narrow-phase | More expensive | Precise check only on pairs that survived broad-phase |

Physics engines, GPU renderers, ray tracers, spatial indexes — same idea
everywhere. Our `aabb_overlap` is the broad phase; the mask slice is the
narrow phase.

For our app the savings are modest (we typically have a handful of people
per frame). The **structure** is what matters: a reviewer reading
`bbox_overlaps_roi` sees the textbook two-step pattern, which is what
production code looks like.
