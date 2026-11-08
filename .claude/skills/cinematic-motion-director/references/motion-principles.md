# Motion Principles

The craft layer: what makes motion feel directed instead of "moved by code".
Numbers assume 30 fps and a 1080-wide canvas; scale with `fps` and canvas width.

## 1. Timing and spacing

**Timing** = how many frames a move lasts. **Spacing** = how far the object travels between
consecutive frames. Two moves with the same timing feel completely different with different
spacing. That is what an After Effects graph editor controls, and what an easing curve
encodes in code.

- Even spacing (linear) reads as mechanical. Use it only for mechanical things: tickers,
  film strips, conveyor belts, constant camera drift, rotating loaders.
- Spacing bunched at the end (ease-out) reads as an object arriving with intent.
- Spacing bunched at the start (ease-in) reads as an object leaving / gaining speed.
- Bunched at both ends (ease-in-out) reads as something travelling from A to B under control.

Visualise spacing when in doubt: render the object's position every 2 frames as ghost dots
(the kit's showcase does this). Good motion shows dense dots where the eye should rest.

### Duration guide (30 fps)

| What | Frames | Seconds |
|------|--------|---------|
| Micro feedback (tick, flash, small scale pop) | 4–8 | 0.13–0.27 |
| Small element / label / icon entrance | 8–14 | 0.27–0.47 |
| Headline line entrance | 12–20 | 0.4–0.67 |
| Large object crossing the frame | 18–30 | 0.6–1.0 |
| Scene transition | 10–24 | 0.33–0.8 |
| Camera push / dolly (background motion) | 45–150 | 1.5–5 |
| Exits | ~60–70% of the matching entrance | |

Bigger and heavier things take longer. Exits are faster than entrances: the viewer has
already read the element.

## 2. Easing by intent

| Intent | Curve (kit name) | Bezier |
|--------|------------------|--------|
| Confident arrival (default entrance) | `ease.out` | 0.16, 1, 0.3, 1 |
| Gentle arrival, secondary elements | `ease.outSoft` | 0.25, 1, 0.5, 1 |
| Leaving, accelerating away | `ease.in` | 0.7, 0, 0.84, 0 |
| Travel A→B, camera, morph | `ease.inOut` | 0.65, 0, 0.35, 1 |
| Whip / energy / hard beat | `ease.snap` | 0.85, 0, 0.15, 1 |
| Wind-up before a move | `ease.anticipate` | 0.36, 0, 0.66, -0.56 |
| Pass the target and settle | `ease.overshoot` | 0.34, 1.56, 0.64, 1 |
| Physical settle, no bounce | `ease.spring` | `Easing.spring({damping: 200})` |
| Playful bounce | `ease.bouncy` | `Easing.spring({damping: 12, stiffness: 120})` |

Rules:
- Never ease-in an entrance (it starts slow and hits the target at full speed — feels like a crash).
- Overshoot and bounce are spices: one element per beat, and only where the brand tone allows.
- Animate `scale` with `output: 'perceptual-scale'` in `interpolate()` when going through large
  ranges, so growth looks even.
- Multi-keyframe moves can use a different easing per segment (`easing: [a, b, c]`).

## 3. The classical principles that matter most on screen

- **Anticipation** — a 3–6 frame counter-move before a big action prepares the eye.
  Use for hero moves and reveals, not for every label.
- **Overshoot & settle** — the object passes its target by 3–8% and returns. Sells weight.
- **Follow-through & overlapping action** — parts of a group do not stop together. Offset
  siblings by 2–4 frames (stagger). Child elements land after their container.
- **Secondary motion** — a subtle response to the main move (shadow stretch, a line
  extending, background parallax). It should never be noticed on its own.
- **Arcs** — natural travel curves slightly; a straight diagonal looks robotic. Add a small
  perpendicular offset or rotate a few degrees along the way.
- **Holds** — a move needs a still after it. Without holds nothing reads and everything
  feels equally important. A hold is not "nothing happening": slow camera drift and grain
  keep the frame alive.
- **Squash & stretch** — almost never on typography; occasionally on shapes in playful
  directions.

## 4. Hierarchy and rhythm

- What moves first is read first. Order entrances by importance, not by layout position.
- One hero move per beat. Everything else supports it with smaller, softer, later motion.
- Rhythm = contrast: fast/slow, loud/quiet, full/empty, cut/flow. A video where every
  element moves at the same speed with the same curve feels monotonous however polished.
- Build an intensity curve for the whole video: hook (high) → context (medium) → mechanism
  (rising) → payoff (peak) → CTA (calm, legible). Ads compress this but keep the shape.
- Cut on action: start the incoming scene's motion before the outgoing one has fully
  stopped, so the energy carries across the cut.

## 5. Kinetic typography

Type is a performer, not a caption.

- Break lines by meaning, not by width. "sem abrir / o After Effects" ≠ "sem abrir o After / Effects".
- Emphasis comes from ONE of: scale jump, weight change, color accent, isolation on screen,
  a dedicated move. Combining several on the same word dilutes all of them.
- Size ladder (1080 wide): display 160–260, h1 100–140, h2 64–90, body 44–56, labels 26–34.
  Vertical video tolerates bigger display type than you think; phones are small.
- Display type: tight tracking (−0.03 to −0.06 em), line-height 0.95–1.05.
  Labels: mono or small caps with positive tracking (+0.04 em).
- Words on screen at once: 1–7 for hooks and ads, up to ~12 for explainer statements.
  More than that is a caption track, not kinetic typography.
- Match reveal speed to speech: word stagger ≈ narrator's word rate (2.5–3.2 words/s →
  stagger ~9–12 frames per word if synced to voice; 2–4 frames when the line appears as
  a typographic gesture before being read).
- Letter-by-letter is for 1–2 word monuments. Sentences go word-by-word or line-by-line.
- Read-time minimum after a line is fully in: `0.4 s + 0.3 s × words`.
- Avoid: rotating whole sentences, typewriter for anything but code, text bouncing in from
  four directions, all-caps paragraphs, centered paragraphs longer than 3 lines.

## 6. Camera

Every camera move has a meaning. Pick by meaning:

| Move | Meaning | Typical |
|------|---------|---------|
| Push-in (zoom 1 → 1.05–1.15) | intensity, focus, "listen to this" | slow, `inOut`, 2–5 s |
| Pull-out | reveal context, "the bigger picture" | `out`, 1–2 s |
| Lateral dolly | progression, list, timeline | `inOut`, steady |
| Tilt / vertical travel | hierarchy, going deeper, stack of steps | `inOut` |
| Roll (≤ 3°) | tension, unease, energy | combine with push |
| Whip pan | hard transition, energy spike | `snap` + motion blur, 6–12 frames |
| Orbit (3D) | product hero, object exploration | real 3D only |
| Handheld drift (2–6 px) | documentary, human, "alive" holds | constant, never on top of a whip |
| Locked-off | clarity, data, CTA | default for reading moments |

Parallax: 3 depth planes are enough. Background 0.2–0.4, subject 1, foreground 1.2–1.6.
The camera should support the information, never compete with it — reduce camera motion
while dense text is on screen.

## 7. Depth, light and materials

- Establish one light direction per video; shadows, gradients and highlights agree with it.
- Depth cues, from cheap to expensive: scale, overlap, parallax, atmospheric fade
  (lower contrast in the back), blur on the background (6–20 px), real 3D.
- Grain (4–10% opacity) removes the sterile digital look of flat gradients. Vignette pulls
  focus in dark directions. Both are seasoning; if noticed, they are too strong.
- Glow is light: it needs a source and a reason. A glowing UI card with no light source
  looks cheap.

## 8. Motion blur

Fast moves (> ~40 px per frame) strobe without blur. Options in Remotion:
`<CameraMotionBlur>` / `<HtmlInCanvasMotionBlur>` from `@remotion/motion-blur`, or the
`blur` presentations for transitions. Use on whips, fast slides and spins; never on slow
moves (it only softens the image).

## 9. Sound sync

- Visual accents land ON the stressed syllable or beat, or 1–2 frames before. Late accents
  feel sloppy; early by more than ~3 frames feels disconnected.
- Cuts on beats; holds on sustained notes; silence (visual and audio) before the payoff.
- Narration is king: duck music under voice (roughly −15 to −20 dB relative), SFX short and
  under the voice. Never place a whoosh on top of a key word.
- Derive cue points from the audio (captions/transcript timestamps), then convert with
  `cues(fps, {...})`. Don't guess timings by watching.
- Sound-off viewing is the default on social: the story must work muted. On-screen text
  carries the message; audio adds energy.

## 10. Field numbers (measured in director-grade prompts, Oct 2026)

Defaults worth starting from — tune by eye after the first review sheet.

| Thing | Number |
|-------|--------|
| UI shape spring | damping ratio ~0.7 (tiny overshoot), settles ~0.35–0.4 s — kit `SHAPE_SPRING` |
| Camera spring | critically damped (1.0), settles ~0.6 s, AFTER the subject — kit `CAMERA_SPRING` |
| Morph / glide | 0.5–0.8 s, e.g. cubic-bezier(.45,0,.15,1); camera zoom rides the same curve |
| Word pull-up | 20 px → 0 over 0.6 s, stagger 0.08 s, cubic-bezier(.16,1,.3,1) |
| Content swap inside a morph | ~12 px blur + fade over ~0.15 s; enter after the container starts, leave before the next morph |
| Beat anticipation | start the move ~0.05 s (1–2 frames) before the beat so the peak lands ON it |
| "Arrive fast, land soft" | cover ~12–19% of the remaining distance per frame (exponential approach) |
| Stagger | 2–4 frames; 1/16 note at 120 BPM = 125 ms |
| Cursor speed | ≤ ~65 px/frame at 60 fps; aim where the target will be |
| Promo density | a new visual idea about every 1–1.5 s; 12–15 compositions per 30 s |
| Holds | no frozen hold > ~1 s — put a slow push (1.03–1.07) or breath on it; but give the key line ≥ 400 ms of real stillness and a 0.7 s reading hold |
| Feature on screen | ≥ 2.5 s when the viewer must follow a UI action |
| Reading size | ≥ 64 px for the phrase being read (1080 wide); motion blur never on active text |
| Motion-blur samples | 4–6 normal moves; 8 for whips (fewer ghost) |
| Loudness | −14 LUFS integrated; voice 10–15 dB over music |

**Holds vs. density.** These don't conflict: text stays readable for its full read time
(§5) while *something else* keeps evolving — a slow push, a breath, a counter, the cursor.
What must not happen is the whole frame freezing (`rhythm-audit` flags it).

**Camera grammar from the field:** one eased move per scene; never zoom in then straight
back out; never reverse direction mid-move; zoom in log space for big scale changes; the
camera eases slower than the subject; each gesture motivates the next camera move.
