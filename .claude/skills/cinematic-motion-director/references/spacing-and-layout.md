# Spacing & Layout (zero-overlap rule)

Spacing is not polish, it is correctness. **No element may ever overlap another element**
unless the overlap is the designed effect (a marker behind a word, a card shadow). Text on
text, text on the caption band, a credit on a brand chip, a growing shape on its own label —
each of these is a bug, and a viewer reads it as amateur work instantly.

This page exists because a real delivery shipped with six overlaps after one layout change
(a panel got 80 px shorter): photo credits collided with the brand chip, a box that scales up
covered its label, a list of chips ran into a grid of dots, and a headline sat on top of the
captions. Every one of them was invisible in the 1-still-per-second storyboard sheet.

## 1. Zones first, then content

Define the zones as numbers in the direction file before placing anything, and keep a
**gap ≥ 32 px** between zones:

| Zone (9:16, 1080 × 1920) | Typical band | Owner |
|---|---|---|
| Top platform UI | y 0 – 220 | nothing important |
| Brand chip / kicker row | y 140 – 290 | brand chip, one kicker |
| Content area | y 290 – (caption top − 40) | the scene's hero + support |
| Caption band | ≈ 100 px tall, fixed y | captions only |
| Bottom platform UI | last ~320 px | nothing important (a face/camera is fine) |

Split screen (motion on top, camera below): the caption band sits on the seam. The content
area of the top panel ends **40 px above the caption top**. When the panel height changes,
every bottom-anchored element moves — re-check all of them.

Rules:
- One owner per zone. Photo credits live in **one** fixed spot that nothing else uses
  (e.g. bottom-right of the panel, above the caption band), never next to the brand chip.
- Size from the box, not from the text: long words (`investimentos`) need a smaller size
  or the line must be allowed to wrap. Never let a word run past the 60 px side margin.
- Stacks (kicker → headline → sub → chips → grid) use **flow layout with explicit
  margins**, not independent absolute positions that can drift into each other.
- A label that sits above a big word needs `marginBottom` ≥ 0.15 × the word's font size.
- Grids/lists that grow with the voice (people icons, dots, chips) must be sized for their
  **final count** — compute the last row's bottom and keep it inside the content area.

## 2. Animated elements: check the extreme, not the average

Collisions happen mid-animation or at the end of a grow:
- Anything that scales, grows or travels: check the frame where it is **largest/farthest**
  (end of the grow, peak of an overshoot, punch-in zoom applied).
- Overshoot (`ease.overshoot`) adds ~10 % — leave that much room.
- Camera pushes and punch-ins scale the whole layer: 1.06 × on a 1020 px panel moves the
  bottom edge ~60 px. Keep that margin, or exclude the caption band from the push.

## 3. Timing literals: local vs absolute

Most overlap/“missing element” bugs in shot-based edits are unit bugs: a helper expects
**seconds local to the shot** and gets an **absolute cue** (e.g. `start={33.19}` inside a shot
that lasts 3 s → the element never appears, or appears on top of the next shot's content).
- Write one helper per shot (`useAt(shotStart)`) that converts absolute cues to local time,
  and pass absolute cues only through it.
- After any re-timing (cutting breaths, changing speed), map every cue through the same
  time map; never hand-edit numbers.

## 4. Mandatory per-shot check (before every delivery)

The 1-still/second sheet is for rhythm. It is **not** enough for spacing. After **any**
layout, timing or copy change:

1. List every shot `[from, to]`.
2. Render 3 frames per shot: `from + 0.3 s`, middle, `to − 0.05 s` (plus the peak of any
   grow/scale), at ≥ 360 px wide — `review-frames.mjs --frames <list>` or extract from the
   render with ffmpeg `select`.
3. Tile them (6 × 2 per image) and inspect **every** tile for: text touching text, text
   touching the caption band, credits vs chips, grown shapes vs labels, clipped words,
   elements past the side margins.
4. Fix, re-render the same frames, repeat until a full pass finds nothing. Only then
   render the final.

State in the delivery message that this pass was done (and how many shots were checked).
