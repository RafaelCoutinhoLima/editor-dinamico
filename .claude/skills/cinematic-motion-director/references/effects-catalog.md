# Effects & Transitions Catalog

Verified against Remotion **4.0.535** package exports (October 2026). APIs move fast: run
`npx remotion versions` in the project and check https://www.remotion.dev/docs before using
anything marked with a minimum version.

**Selection rule:** pick the transition from the *relationship* between the two scenes,
not from the list. If you can't say why a transition is there in one sentence, use a cut.

## 1. Transitions — `@remotion/transitions`

Used inside `<TransitionSeries>`: `<TransitionSeries.Transition presentation={…} timing={…} />`.
Timings: `linearTiming({durationInFrames, easing?})`, `springTiming({config, durationInFrames?})`.
A transition overlaps both scenes, so it **shortens** the total duration by its length.
`<TransitionSeries.Overlay>` (≥ 4.0.415) renders on top of a cut without shortening it.
Rules: no two transitions/overlays adjacent; a transition can't be longer than its neighbours.

### DOM presentations (work everywhere, including preview in any browser)

| Import | Meaning / when | Avoid when |
|--------|----------------|------------|
| *(none — hard cut)* | Energy, contrast, comedic jolt, beat drops. The most professional transition. | — |
| `fade` from `/fade` | Time passing, calm, emotional softness, end cards | Fast-paced ads (feels sleepy) |
| `slide({direction})` from `/slide` | Next item in a sequence, spatial continuity, "swipe" language | Every cut in the video |
| `wipe({direction})` from `/wipe` | Replacement, before → after, chapter change | Soft emotional moments |
| `flip({direction, perspective})` from `/flip` | Reverse side, card turn, "the other side of the story" | Serious/corporate tone |
| `clockWipe({width, height})` from `/clock-wipe` | Time, countdown, cycles | Anything not about time |
| `iris({width, height})` from `/iris` | Focus on a point, vintage, spotlight | When the focal point isn't centered (use kit `IrisReveal` with cx/cy) |
| `pushCut({...})` from `/push-cut` | Punchy push with optional flash; hype, trailers | Calm content |
| `none()` from `/none` | Keep both scenes mounted without a visual blend (to animate manually) | — |

### Shader presentations (HTML-in-canvas)

Rendering works out of the box (verified: `zoomBlur` renders via CLI with no flags).
**Live preview in Studio** requires Chrome with `chrome://flags/#canvas-draw-element`; they
don't preview in Firefox/Safari. Tell the user this before relying on them.

| Import | Meaning / when |
|--------|----------------|
| `zoomBlur({rotation?})` from `/zoom-blur` (≥ 4.0.456) | Speed, impact, "zoom into the idea" |
| `crossZoom({strength?})` from `/cross-zoom` | Rush between ideas, montage energy |
| `dreamyZoom({rotation?, scale?})` from `/dreamy-zoom` | Memory, imagination, soft dream |
| `zoomInOut({})` from `/zoom-in-out` | Pull back then dive in |
| `linearBlur({intensity?})` from `/linear-blur` | Motion-blurred push, whip-like |
| `blurSlide({direction?, blur?})` from `/blur-slide` | Slide with motion blur; premium UI swipes |
| `filmBurn({seed?})` from `/film-burn` | Analog, nostalgia, documentary, behind-the-scenes |
| `dissolve({…})` from `/dissolve` | Burning/disintegrating edge; transformation |
| `crosswarp` from `/crosswarp` | Liquid warp morph |
| `ripple` from `/ripple` | Water, sound wave, disturbance |
| `swap({reflection?, perspective?, depth?})` from `/swap` | 3D card swap; product/option comparisons |
| `bookFlip({direction?})` from `/book-flip` | Page turn, story, editorial |

### Transitions you build (kit / custom)

- **Match cut** — end scene A on a shape/position/color and start scene B with the same one
  (a dot becomes a logo, a word becomes a UI label). Strongest storytelling transition.
  Implement as a hard cut with continuity, or kit `IrisReveal` from the shared focal point.
- **Shape wipe** — a brand shape scales up to cover the frame and reveals the next scene.
- **Type transition** — a word stays while everything around it changes; or the word scales
  until its counter fills the frame.
- **Whip pan** — `Camera` x moves 1–2 frame widths in 6–10 frames with `ease.snap` + motion
  blur, cut at the midpoint.
- **Light leak / flash over a cut** — `TransitionSeries.Overlay` with a light leak (below).

## 2. Visual effects — `@remotion/effects` (≥ 4.0.464)

Applied through the `effects` prop of canvas-based components: `<Solid>`, `<HtmlInCanvas>`,
`<Img>`, `<CanvasImage>`, `<AnimatedImage>`, `<Video>` (`@remotion/media`), `<Gif>`, and
`@remotion/shapes` components. Plain divs/`<AbsoluteFill>` don't accept it — wrap them in
`<HtmlInCanvas>` (which needs the Chrome flag for preview).

Import per effect: `import {blur} from '@remotion/effects/blur'`. Effects don't animate by
themselves: drive their params from `useCurrentFrame()`.
Most use WebGL2 → add `Config.setChromiumOpenGlRenderer('angle')` in `remotion.config.ts`
(or `--gl=angle`).

| Group | Effects | Use for |
|-------|---------|---------|
| Color & tone | `brightness`, `contrast`, `exposure`, `saturation`, `vibrance`, `hue`, `tint`, `duotone`, `grayscale`, `levels`, `lut`, `colorCorrection`, `whiteBalance`, `shadowsHighlights`, `thermalVision`, `invert`, `linearGradientTint`, `colorKey` | Grading footage into the direction's palette; duotone for brand-colored footage |
| Blur | `blur`, `zoomBlur`, `linearProgressiveBlur`, `radialProgressiveBlur`, `regionBlur`, `lightTrail` | Depth of field, focus pulls, speed |
| Light | `glow`, `lightLeak`, `shine`, `starburst`, `vignette`, `dropShadow` | Only with a motivated light source |
| Distortion | `chromaticAberration`, `barrelDistortion`, `fisheye`, `wave`, `noiseDisplacement`, `cornerPin`, `mirror`, `skew`, `scale`, `tile`, `uvTranslate`/`xyTranslate` (`/translate`) | Glitch beats, lens character, screen replacement (`cornerPin`) |
| Texture | `noise`, `whiteNoise`, `paper`, `halftone`, `scanlines`, `dotGrid`, `gridlines`, `lines`, `pattern`, `burlap`, `flannel`, `speckle`, `emboss`, `contourLines`, `liquidContours`, `rings`, `waves`, `zigzag`, `checkerboard`, `tvSignalOff` | Material identity (print, retro TV, risograph) |
| Edges | `outline`, `roughenEdges`, `shrinkwrap`, `tear` | Collage, cut-paper, sticker looks |
| Pixel / reveal | `pixelate`, `pixelDissolve`, `evolve`, `linearProgressivePixelate`, `radialProgressivePixelate`, `venetianBlinds` | Digital reveals, "rendering" metaphors |

Custom effects: `createEffect()` from `remotion` (2d / webgl2 / webgpu backends).

## 3. Motion blur — `@remotion/motion-blur`

| Component | Notes |
|-----------|-------|
| `<HtmlInCanvasMotionBlur width height shutterAngle samples>` (≥ 4.0.529) | Best quality; samples sub-frames. Preview needs the Chrome flag; render needs no setup. |
| `<CameraMotionBlur shutterAngle samples>` | Works without HTML-in-canvas; layered blending may shift colors/opacity slightly. |
| `<Trail>` | Stylised echo of previous positions, not realistic blur. |

`shutterAngle` 180 = film look. Samples 6–10 is usually enough; more = slower renders.
Whips and very fast slides ghost with 4 samples — use 8. Never blur text that is being read.

## 4. Light leaks

`lightLeak({progress, seed, hueShift})` from `@remotion/effects/light-leak` on a `<Solid>`,
usually inside `<TransitionSeries.Overlay>` (≥ 4.0.500). Animate `progress` 0→1.
Warm (default) for nostalgia/lifestyle; `hueShift: 240` for cool tech. One per video,
two at most — a leak on every cut is a template smell.

## 5. 3D — `@remotion/three`

`<ThreeCanvas width height>` + React Three Fiber (peer deps: `three`, `@react-three/fiber`).
Animate only from `useCurrentFrame()` (never R3F `useFrame()`); include lights.
Use real 3D for: extruded type with lighting, products, orbiting cameras, depth-of-field
scenes, particle fields with true perspective. Use the kit's 2.5D `Camera`/`Layer` for
everything else — it is faster to render and easier to art-direct.

## 6. Kit effects (no extra packages)

`Grain`, `Vignette`, `GridReveal`, `DrawLine`, `IrisReveal`, `Highlight`, `Scramble` — see
`motion-kit/README.md`. They are plain DOM/SVG and preview in any browser.

## 7. Recommended combinations

| Moment | Combination |
|--------|-------------|
| Hook | Hard cut in + monumental type (`MaskReveal`/`CharCascade`) + slow push-in. No transition effect. |
| Concept / system | `GridReveal` + `WordStagger` + locked camera; elements snap to the grid |
| Mechanism / process | `DrawLine` connecting stages + `Scramble` for the "code/AI" stage + vertical camera travel |
| Before → after | `wipe` or split screen; same layout, only the treatment changes |
| Energy spike | Whip (`ease.snap` + motion blur) or `zoomBlur`; immediately followed by a hold |
| Nostalgia / analog | `filmBurn` or light leak + grain + slight gate weave (drift 1–2 px) |
| Proof / numbers | `CountUp` + `Highlight` on the unit; locked camera; hold ≥ 1 s |
| CTA | `fade` or cut, locked camera, one `Highlight`, generous hold (≥ 1.5–2 s) |

## 8. Smells (fix on sight)

- A different transition on every cut.
- Glow + blur + particles + light leak in the same scene.
- Overshoot on every element.
- Camera moving during dense text.
- Effects that hide the product or the words.
- Shader transitions in a project whose user previews in Safari, without warning them.
