# Quality Checklist

Run on review stills (`scripts/review-frames.mjs`) and on the full render. Fix, re-render
the affected frames, repeat. Report honestly which items were checked.

## Direction
- [ ] The video has one visual metaphor and every scene belongs to it
- [ ] Palette, type and shapes follow the direction file; no off-system colors or fonts
- [ ] Transitions follow the transition grammar; no random transition per cut
- [ ] Effect budget respected (≤ 1 signature effect per scene; overshoot on ≤ 1 element per beat)
- [ ] It does not look like a slideshow, a stock template or a corporate deck

## Inputs
- [ ] Every claim, number, feature, logo and UI on screen comes from the user's real inputs
- [ ] Nothing on the direction's prohibition list appears

## Story & rhythm
- [ ] Frame 0 is not empty: the hook opens already in motion and works as a thumbnail
- [ ] Hook works in the first 1–2 s, even as a still
- [ ] Storyboard sheet (1 still/s) reviewed and approved before the full render
- [ ] `rhythm-audit.mjs` run on the render; every flag either fixed or justified
- [ ] With music: `beat-map.mjs` used; cuts land on beats (`rhythm-audit --beats`), video length = whole bars
- [ ] No single-frame pops; loops pass `rhythm-audit --loop` (last frame leads into frame 0)
- [ ] Independent critic pass done (fresh subagent or harsh self-review), verdict "ship"
- [ ] Each scene has one job and one hero move
- [ ] Intensity curve has peaks AND pauses; the CTA is calm and long enough
- [ ] Duration matches the real audio; nothing was compressed to fit an arbitrary length
- [ ] Visual accents hit the voice/music beats (± 2 frames)

## Motion craft
- [ ] No linear motion except intentional mechanical movement
- [ ] Entrances decelerate, exits accelerate, travels ease in-out
- [ ] Staggers/overlaps feel organic (2–4 f offsets), nothing stops all at once
- [ ] Every move is followed by a readable hold
- [ ] Camera never moves fast while dense text is on screen
- [ ] Fast moves have motion blur or are short enough not to strobe

## Typography & layout
- [ ] Line breaks by meaning; one emphasis treatment per line
- [ ] Sizes ≥ 44 px body / 30 px labels on a 1080-wide canvas
- [ ] Text contrast ≥ 4.5:1 over everything behind it
- [ ] Read time ≥ 0.4 s + 0.3 s × words after fully visible
- [ ] Everything aligned to the grid; margins consistent
- [ ] Critical content inside the platform safe zone (check with `SafeZoneGuide`)
- [ ] No clipped descenders, no text touching frame edges, no collisions mid-animation
- [ ] **Zero overlaps** — per-shot pass done (3 frames per shot: start+0.3 s, middle, end, plus
      the peak of any grow/scale), see `references/spacing-and-layout.md`; re-done after every
      layout/timing change
- [ ] Every zone has one owner; ≥ 32 px between zones; content ends ≥ 40 px above the caption band
- [ ] Photo credits in one fixed spot that nothing else uses

## Talking head / real footage
- [ ] Breaths and dead air removed (`scripts/cut-breaths.py --verify`), speed-up applied after the cut
- [ ] Every cue re-timed through the time map; nothing hand-shifted

## Sound
- [ ] SFX aligned by their measured sync point (onset / whoosh peak), not file start; within 1 frame, never late by 2
- [ ] Effects from the earshot bank or real recordings, not raw oscillator beeps; every take passed the audit
- [ ] Round robin: no take repeated twice in a row; runs keep their gap and end on one accent
- [ ] Restraint: riser → stop-down → hit at most twice; no big hit on a key word; effects 20–25 dB under the voice (UI) / 3–10 dB over a music bed
- [ ] First sound within ~0.15 s; the ending lands at body level with a short fade
- [ ] Loudness ≈ −14 LUFS; voice clearly over music; a music-only version exported if useful

## Technical
- [ ] Deterministic: no Math.random/Date/CSS animations/`useFrame`; re-render is identical
- [ ] Fonts loaded via `loadFont`; no fallback font visible in any frame
- [ ] Media premounted; no pop-in on the first frame of a sequence
- [ ] Every scene paints its background (transitions don't leak the other scene)
- [ ] No hold frame shows an unfinished animation (scramble, count, stagger still running)
- [ ] Remotion packages + zod on matching versions; render has no warnings worth fixing
- [ ] Final file plays, has audio (if any), right size/fps/duration

## Before delivering (6 checks)
- [ ] Hook on screen in the first 0.5 s, no black or empty first frame
- [ ] Duration, format(s) and fps match the brief; every requested format delivered with its own spacing pass
- [ ] All on-screen text legible on a phone and correctly spelled
- [ ] Music is the user's, the client's (in writing) or generated in code
- [ ] No third-party character, mascot or brand used as decoration in paid work; code/assets from other repos checked for license
- [ ] Contact sheet reviewed and approved cut by cut (one-fix loop: worst stretch named, fixed, re-rendered)
- [ ] Illustrated characters, logos and brand cards never cropped (hands, feet, edges visible)

## Before posting (from the field)
- [ ] The final MP4 opens and plays on a phone (not only the preview or the contact sheet)
- [ ] 9:16 at 1080 × 1920, text away from the top ~220 px and bottom ~320 px
- [ ] Every number and fact on screen was checked before the render (two sources for explainers)
- [ ] No AI-generated face of a real person, no brand logo used as decoration
- [ ] Ads use the client's own character, never a third-party mascot (e.g. Clawd)
- [ ] Logos checked on their final background (white header logos vanish on light paper)
- [ ] Paid generation (AI clips, keyframes) logged with its credit cost
- [ ] `references/never-do.md` read against this video

## Delivery
- [ ] Final render path, source path, and how to edit text/timing/colors
- [ ] What was rendered and checked is stated; what was not is stated too
