# Alerting

Print `ALERT: Person in restricted area` when someone is in the ROI —
without spamming the terminal. Lives inline in [detect.py](../src/detect.py)
→ `main` because it's just a few lines.

## The rule

```python
if person_in_roi and (now - last_alert_at) >= ALERT_COOLDOWN_SEC:
    print(f"[{stamp}][frame {frame_idx}] ALERT: Person in restricted area")
    last_alert_at = now
```

Two conditions both need to hold:

1. **Someone is currently in the ROI** (this frame).
2. **At least 2 seconds have passed** since the last alert printed.

`ALERT_COOLDOWN_SEC = 2.0` is defined in [config.py](../src/config.py).

## Why a cooldown

Without it, the script would print 10–30 alerts per second while a person
stood in the zone. The terminal would scroll past anything useful and you
couldn't visually correlate alerts with what's happening on screen. 2
seconds is short enough to feel responsive but long enough to be readable.

## Output format

```
[17:09:50][frame 17] ALERT: Person in restricted area
```

- **Wall-clock time** so you can correlate with real-world events.
- **Frame index** so you can scrub a saved MP4 to the exact frame and
  verify the alert was correct.

## What this is *not* doing

- **Not state-change-based.** It re-fires every 2 seconds while the
  condition holds, instead of firing once on entry and going silent.
  Tracking would let us do entry/exit transitions per person ID.
- **Not persistent.** Alerts go to stdout only. To save them, redirect:
  `python src/detect.py ... | tee alerts.log`.
- **Not external.** No webhooks, no email, no Slack push. Print only.

These are listed in the README's "Limitations" section as honest caveats.
