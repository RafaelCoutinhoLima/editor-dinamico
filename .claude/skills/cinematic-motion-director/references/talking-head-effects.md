# Talking-head effects: depth, face-anchored graphics, effect showcases

What viral "Claude edits my video" reels do on top of a person talking to camera, and how to build
each in Remotion. Studied 2026-10-26: two showcase reels (a 17-effect list and a 36-effect
"/effects" demo) and the MIT repo github.com/Vibha-Ramprakash/claude-video-effects (42 starter
effects in Python/OpenCV; models: YuNet face detector, MIT; MediaPipe Selfie Segmenter,
Apache-2.0). Method only: no code, wording or footage copied from them.

## 1. The core trick: three depth planes

Nearly every effect is the same structure — the graphic sits **behind the person**, or is
**anchored to the face** without covering it:

```
base video  →  BEHIND layers (giant word, wall of cards, orbit back half)  →  person cutout
            →  ANCHORED layers (chips, brackets, orbit front half)  →  FRONT (captions, counters)
```

1. `python scripts/person-matte.py talk.mp4 --out public/me [--start s --end s]` →
   `person.webm` (speaker on transparent pixels, VP9 alpha) + `face.json` (smoothed face centre
   and width per frame, forward+backward filter so it has no lag). ~4–5× real time on a
   1-core laptop; models download once (~1 MB + 0.2 MB).
2. `motion-kit/depth.tsx`: `<DepthStack base person camera behind anchored front/>`,
   `useFace(track)`, `faceZoom()` (push-in capped at 2×), `faceOnScreen()` (face after the
   zoom, for front cards), `placeBeside()` (first spot right/left/above/below that stays inside
   the frame and off the face), `coversFace()` (spacing-pass check), `fxWindow()` (in/out
   envelope).
3. Check: render a still in the middle of each effect window and look — text over the face,
   cut by the edge or unreadable gets moved or shortened. Add the face box to the 3-frames-per-
   shot spacing pass.

Rules: **never cover the face** (everything goes behind or beside it) · camera effects first
when windows overlap (push-in, spotlight, lock-on), graphics after · zoom ≤ 2× · one effect
window 1.5–4 s · the effect starts on the word that names it (word timings from Whisper) ·
the mic and hands count as foreground — fine, they stay in front.

## 2. Effect catalog (build recipes)

Names are ours; pick by what the sentence says. B = behind layer, A = anchored, F = front.

| effect | what the viewer sees | build |
|---|---|---|
| **Backdrop word** | a giant word drops in behind the head | B: one word, 800 weight, 250–330 px, accent color, rise + scale 0.92→1 |
| **Spotlight** | room goes dark, the speaker stays lit, glowing word behind | base darkened (brightness 0.35 + vignette), B: word with glow; person cutout untouched |
| **Lock-on** | corner brackets snap onto the face, camera follows | A: 4 L-brackets around `useFace` box (overshoot in), `faceZoom` 1.2–1.35 |
| **Lean-in / slow push** | punch-in on one word / slow push while the room blurs | `faceZoom` 1.3–1.45 in 6 frames on the word; slow push 1→1.4 over 3 s with base blur 0→8 px (cutout stays sharp) |
| **Orbit / carousel** | thumbnails circle the head, behind at the top, in front at the bottom | items on an ellipse around the face; angle sin < 0 → B, else A; scale by depth |
| **Wall of cards** | screenshots/headlines/reels pile up behind the head, one every ¼ s | B: cards with small random rotation (seeded), shadow, stagger 6–8 frames; a total pops in F at the end |
| **Lineup / fan** | numbered tiles fan out in an arc above the head | B: tiles on an arc above `face.cy - face.w`, stagger, numbers in mono |
| **Checklist under the chin** | a task card whose steps spin, then tick, on the words | A: glass/dark card below the face (`placeBeside` below), each row: spinner → check on its word time; counter "3 of 5" |
| **Toggles** | phone settings card flips switches on, line by line | A: rows with iOS-style switches, one per word cue, accent when on |
| **Glass widgets** | frosted cards (big number, mini chart, profile chip, "Edited by" pill) float around the head | A/B: `backdropFilter: blur(18px)` cards + 1 px white border at 30 %, slow drift, never over the face |
| **Graph climbs** | a glass card under the chin, line/bar graph climbs while the number counts up | A: `CountUp` + bars growing with stagger, accent on the last bar |
| **Headline split** | a headline card slides down, the speaker is pushed to the bottom half | F: card top half; base + cutout translated down 35 % |
| **Magazine cover** | the speaker becomes a cover: masthead behind the head, cover lines in front | B: masthead serif/condensed; F: issue line + 3 cover lines on the sides |
| **Comment / follow** | a comment bar types a word and posts; a Follow button flips to Following | F: social UI, typed with keyboard SFX, cursor press + `click` SFX on the flip |
| **Stamp / sticker** | a big stamp slams in, small shake | F: rotated −8°, scale 1.6→1 in 5 frames, 2-frame camera shake, `hit` SFX |
| **Freeze & point** | freeze frame, hand-drawn arrow points at the speaker with a label | hold one frame (`startFrom` fixed), arrow path drawn with `DrawLine`, marker-style label |
| **Dot reveal** | the shot builds out of glowing dots, then snaps to the picture | grid of dots sampling the frame luminance (pre-extracted), grow → crossfade to video in 8 frames — doubles as the "processing…" transition |
| **Timeline / render look** | editing timeline with playhead, REC timecode, % rendered | F: timeline strip at the top, playhead moving, progress number counting |
| **Grade / before-after** | moody, b&w, warm grade; a slider wipes before → after | CSS filters on base only (cutout matches or also graded); wipe = clipPath on a second copy |
| **Match-cut word** | news pages cut on one word, the word locked in a box behind the head | B: 4–6 headline crops flashed 3–4 frames each, the word stays in the same box |

## 3. Two reel formats that showcase effects (and grow followers)

**A. The numbered list ("17 effects…")** — the speaker talks to camera the whole time; at the
top a title (2 lines) and the full list of names in two small columns, the current item
highlighted in the accent; in the lower centre a phone mockup plays each demo for ~0.75 s with
an "n/17" chip; after the list the mockup disappears and word-by-word captions return with the
keyword in the accent (one huge word, e.g. "dezenas"); ends on a phone mockup of the profile /
comments for the CTA. Cut rate ~1 demo per 0.75 s keeps a 20 s reel dense.

**B. Command → result** — a phone chat UI: the keyboard types `/effects name` (letters pop as
on iOS), the message sends, a "processing" dot-matrix of the frame appears and resolves into
the edited result, then the result plays full screen for 1–2 s; repeat per effect; end on a
grid of all effects with a comment CTA. Proof-of-tool format: the command is the hook.

Both: the CTA is "comment WORD and I send it" over a mockup of the profile/DM — use it only when
the user really sends something.

## 4. Fabio's defaults on top

Light identity still applies to graphics (ivory cards, ink text, Claude orange #D97757 as the
only accent, Switzer); the footage keeps its own look. Real typing / click SFX from
`scripts/sfx-earshot.py` on typed commands and button presses. Captions stay below the face
and above the safe bottom area.
