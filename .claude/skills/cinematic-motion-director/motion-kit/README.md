# Motion Kit

Drop-in presets for Remotion. Plain TypeScript/React on top of `remotion` — no extra
packages. Tested with Remotion 4.0.535 (`Easing.spring` and CSS individual transform
properties are required; upgrade older projects with `npx remotion upgrade`).

```bash
cp -R <skill-dir>/motion-kit src/motion
```

```tsx
import {MaskReveal, Camera, Layer, tween, ease} from "./motion";
```

All timing props are **frames**. Write them as seconds × fps: `start={0.4 * fps}`.
Every animation is clamped and deterministic.

## easing.ts
| Export | Use |
|--------|-----|
| `ease.out / outSoft / in / inOut / snap / anticipate / overshoot / spring / bouncy / linear` | Curves named by intent (see `references/motion-principles.md`) |
| `tween(frame, [f0, f1], [v0, v1], easing?)` | Clamped `interpolate` |
| `progress(frame, start, duration, easing?)` | 0→1 over a window |
| `mix(a, b, t)` | Blend two numbers by progress |

## direction.ts
`Direction` type (palette, type, layout, motion) and `signalNoir` starter. Make one per
project; scenes read from it.

## text.tsx
| Component | Purpose | Key props | Limits |
|-----------|---------|-----------|--------|
| `MaskReveal` | Line slides out from behind an edge — premium headline entrance | `from: below/above`, `start`, `duration`, `exitAt` | One line per instance |
| `WordStagger` | Words arrive in sequence, mirrors speech | `text`, `stagger`, `mode: rise/mask`, `blur`, `emphasis[]`, `emphasisStyle` | Plain string input |
| `CharCascade` | Characters flip up in 3D | `text`, `stagger`, `charStyle` | 1–2 words |
| `TrackingIn` | Wide tracking collapses while sharpening — calm title | `fromEm`, `toEm`, `blur` | Single line (nowrap) |
| `Scramble` | Glyph noise decodes into text — code/AI/data beats | `stagger`, `flicker`, `seed`, `lockedStyle` | Use a mono font |
| `Highlight` | Marker bar sweeps behind the key word | `color`, `height` | Wraps across lines |

## camera.tsx
`<Camera x y zoom rotate drift>` + `<Layer depth>`: 2.5D camera. depth 0 = screen-locked,
1 = subject, > 1 = foreground. Drive values with `tween`. `useCamera()` reads the state.
Real 3D → `@remotion/three`.

## shapes.tsx
| Component | Purpose |
|-----------|---------|
| `DrawLine` | Any SVG path draws on (connectors, underlines, routes). `viewBox` for custom coordinates |
| `GridReveal` | Editorial grid draws in; structure scenes; keep opacity low |
| `IrisReveal` | Circle reveal from any point (`cx`, `cy` in %) — shape match cuts |
| `CountUp` | Number rolls to value, tabular figures, locale-aware |

## texture.tsx
`Grain` (deterministic SVG noise, `opacity` 0.04–0.1) and `Vignette`.

## formats.tsx
`FORMATS` (vertical, portrait, square, landscape), `SAFE_ZONES` (meta-reels, tiktok,
yt-shorts, feed), `useSafeArea(zone)` → px insets, `<SafeZoneGuide zone>` overlay for review.

## sync.ts
`cues(fps, {name: seconds})` → frames, `span(cues, a, b)`, `estimateSpeechSeconds(text, wps)`.
Music (feed `beats.json` from `scripts/beat-map.mjs`): `beatPulse(frame, fps, beats, decay)`
→ 1 on the hit decaying to 0, `beatIndex(frame, fps, beats)`, `snapToBeat(seconds, beats, fps)`.

## ui.tsx
| Component | Purpose | Key props |
|-----------|---------|-----------|
| `Cursor` | Pointer that travels in arcs and clicks (press + ripple) — cause → effect demos | `path: {x, y, at, click?, travel?}[]`, `travel`, `color`, `ring` |
| `MorphBox` | ONE element morphing size/radius/color/position through states; content leaves fast, enters late, ≤ 4 px blur; same-content states (hover) don't swap | `states: {at, w, h, radius, bg, x?, y?, content}[]`, `duration`, `easing`, `contentOut`, `contentIn`, `blur` |
| `Handoff` | Shared-element transition: one accent carrier travels between states, drawing the source glyph at its start and the target glyph at its end — the accent never disappears | `hops: {at, from, to, dur?}[]` with spots `{x, y, d, node?, onDot?, spin?}`, `color` |

Working example: `showcase/cinematic-motion-director/src/UiMorph.tsx` in the skills repo.

## depth.tsx — behind-the-head depth (import directly)

Feed it `person.webm` + `face.json` from `scripts/person-matte.py`.

```tsx
const f = useFace(face as FaceTrack);                    // {cx, cy, w} px at this frame
const z = interpolate(frame, [0, 90], [1, 1.12]);
const chip = placeBeside(faceOnScreen(f, z, W, H), 260, 80, W, H); // right/left/above/below, off the face
<DepthStack base={staticFile("me/base.mp4")} person={staticFile("me/person.webm")}
  camera={faceZoom(f, z, W, H)}
  behind={<GiantWord />}          // under the person, moves with the camera
  anchored={<Brackets face={f} />} // over the person, moves with the camera
  front={<Chip {...chip} />} />    // screen space: captions, counters, cards placed with faceOnScreen
```
`coversFace(face, box)` for the spacing pass; `fxWindow(frame, from, to)` for in/out envelopes.
Tested with Remotion 4.0.536 (OffthreadVideo `transparent`).

## edit.tsx — voiceover-driven edits
Not exported from `index.ts` (needs `@remotion/media`); import `./motion/edit`.
`EditTimeline({ plan, voice, scenes })` renders an EDIT PLAN (see `references/voiceover-and-footage.md`):
narration slices (`vo`), sound bites with original audio (`bite`), visuals `title` / `kinetic`
(words on their spoken time) / `number` / `broll` (`cover`+`focus` or `contain-blur`) / `image` /
`scene` (your component), TikTok-style captions, "Fonte:" credit tags, drift on type scenes.
Helpers: `planTimeline(plan)` (durations for calculateMetadata), `resolveEditAssets(plan)` (loads
voice map + bite transcripts), `timelineWords(plan, voice)`.

## More in easing.ts / text.tsx
- `springSteps(frame, fps, [{at, value}…], config)` — a value with many targets as a sum of springs (pure function of the frame). `SHAPE_SPRING` (ratio ~0.73) and `CAMERA_SPRING` (critical, slower).
- `Typewriter` — keystroke rhythm with seeded jitter; caret blinks only when idle. Props: `text`, `start`, `cps`, `jitter`.

## Extending
Follow the same contract: props in frames, `progress`/`tween` for every value, a header
comment with **purpose** and **limits**, no `Math.random()`, no CSS animations.
