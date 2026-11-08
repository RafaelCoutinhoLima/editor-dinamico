# Remotion Implementation

How to turn the direction and storyboard into a clean, editable Remotion project.
Verified with Remotion 4.0.535. For any API not shown here, use the official Remotion skills
(`remotion-best-practices`) or https://www.remotion.dev/docs — do not guess.

## 1. Project

New project (empty folder):

```bash
npx create-video@latest --yes --blank --no-tailwind my-video
cd my-video
npx remotion add @remotion/transitions @remotion/google-fonts
```

`npx remotion add <pkg>` installs the version matching the project's Remotion. All
`remotion` / `@remotion/*` packages must share the exact same version (no `^`). If the CLI
reports a version mismatch (including `zod`), fix it before anything else.

Existing project: read `package.json`, `src/Root.tsx` and the existing scenes first; keep
their conventions; don't overwrite user edits.

Install the kit:

```bash
cp -R <skill-dir>/motion-kit src/motion
```

(`<skill-dir>` is where this skill is installed, e.g. `.claude/skills/cinematic-motion-director`
or `.agents/skills/cinematic-motion-director`.)

## 2. Structure

```
src/
  index.ts              registerRoot
  Root.tsx              <Composition>s (one per format/variant family)
  direction.ts          this video's Direction object + fonts
  fonts.ts              loadFont() calls (only weights used)
  motion/               the kit (copied)
  scenes/
    01-Hook.tsx         one component per storyboard scene
    02-Problem.tsx
    ...
  Main.tsx              TransitionSeries / Sequences assembling the scenes + audio
public/
  voiceover.mp3, music.mp3, sfx/, images/, footage/
```

Scenes take their timing from props or from `cues()`; colors/type/sizes from `direction.ts`.
Changing the brand color or the hook duration must be a one-line change.

## 3. Core API you will use

```tsx
import {AbsoluteFill, Sequence, Series, useCurrentFrame, useVideoConfig, interpolate, Easing, random, staticFile} from "remotion";
```

- `useCurrentFrame()` inside a `<Sequence>` is relative to the sequence start.
- `interpolate(frame, [in0, in1], [out0, out1], {easing, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})`
  — or the kit's `tween()` which always clamps.
- Easing: `Easing.bezier(x1, y1, x2, y2)`, `Easing.spring({damping, stiffness, mass})`,
  `Easing.in/out/inOut(fn)`. `spring({frame, fps, config})` also exists for physics values.
- Prefer CSS individual transform properties (`translate`, `scale`, `rotate`) over a
  `transform` string; they are easier to read and edit in Studio. Use `transform` only for
  order-sensitive chains, `skew()` or `perspective()`.
- `random("seed")` for deterministic randomness. Never `Math.random()`.
- Give every `<Sequence>` / `<TransitionSeries.Sequence>` / media element `premountFor={fps}`
  so assets load before they appear.
- CSS `transition`, `animation`, keyframes and Tailwind `animate-*` do NOT render. Refactor
  them to frame-driven values.

### Assembling scenes

```tsx
import {TransitionSeries, linearTiming, springTiming} from "@remotion/transitions";
import {wipe} from "@remotion/transitions/wipe";

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={3 * fps} premountFor={fps}>
    <Hook />
  </TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={wipe({direction: "from-left"})} timing={linearTiming({durationInFrames: 14, easing: ease.snap})} />
  <TransitionSeries.Sequence durationInFrames={4 * fps} premountFor={fps}>
    <Mechanism />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

Total = sum of sequences − sum of transitions. Compute it in code and export it for
`<Composition durationInFrames>`; never hard-code a number that drifts from the scenes.
Every scene must paint its own background, or slides/wipes reveal the other scene through it.

## 4. Fonts

```ts
import {loadFont} from "@remotion/google-fonts/InterTight";
export const display = loadFont("normal", {weights: ["600", "800"], subsets: ["latin"]}).fontFamily;
```

Load only the weights and subsets used (`latin` covers Portuguese/Spanish accents;
add `latin-ext` for Central European languages). Local brand fonts: `@remotion/fonts`
`loadFont({family, url: staticFile(...)})` — see the official `local-fonts` rule.

## 5. Audio and sync

```tsx
import {Audio} from "@remotion/media";
<Audio src={staticFile("voiceover.mp3")} premountFor={fps} />
<Audio src={staticFile("music.mp3")} volume={0.18} premountFor={fps} />
```

- Duration from the real file: use `calculateMetadata` on the `<Composition>` and measure the
  audio (the official skill uses Mediabunny: `new Input({formats: ALL_FORMATS, source: new UrlSource(src)}).computeDuration()`).
- Word timestamps: transcribe (official `remotion-captions` skill; `@remotion/openai-whisper`,
  `@remotion/install-whisper-cpp`) → convert the key words to cue seconds → `cues(fps, {...})`.
- Ducking: drive `volume` with a frame callback (`volume={(f) => …}`) lowering music while
  the voice speaks.
- SFX: short files placed with `<Sequence from={cue.x - 2}>` so the transient lands on the cut.

## 6. Compositions as data (for variants and pipelines)

```tsx
<Composition
  id="Ad"
  component={Ad}
  schema={adSchema}               // zod: validates props, enables Studio editing
  defaultProps={adDefaults}
  calculateMetadata={calculateAdMetadata} // width/height/duration from props
  durationInFrames={300} fps={30} width={1080} height={1920}
/>
```

The `zod` version must match what Remotion expects (the CLI tells you on mismatch).
See `ad-creatives.md` for the full pattern and `showcase/.../AdCreative.tsx` in the skills
repository for a working example.

## 7. 3D

`npx remotion add @remotion/three` (+ `three`, `@react-three/fiber`). Wrap in
`<ThreeCanvas width={width} height={height}>`, add lights, animate only from
`useCurrentFrame()`, never `useFrame()`. Use `Config.setChromiumOpenGlRenderer("angle")`
(remotion.config.ts) for reliable GPU rendering. Load models with `useGLTF`/loaders wrapped
so rendering waits for them (Remotion's `delayRender`/`continueRender` if loading manually).

## 8. Preview, review, render

```bash
npx remotion studio                                   # live preview
node <skill-dir>/scripts/review-frames.mjs --comp Main --count 10 --scale 0.4   # review stills
node <skill-dir>/scripts/review-frames.mjs --comp Main --every 1 --sheet         # storyboard sheet, 1 still/s
node <skill-dir>/scripts/rhythm-audit.mjs out/main.mp4 --audio public/voice.mp3 # rhythm critic on the render
node <skill-dir>/scripts/beat-map.mjs public/music.mp3 --out src/beats.json      # music first: BPM, beats, drop
node <skill-dir>/scripts/rhythm-audit.mjs out/main.mp4 --beats src/beats.json --loop
npx remotion still Main out/frame.png --frame=120     # one frame
npx remotion render Main out/main.mp4                 # H.264 MP4
npx remotion render Main out/main.mp4 --crf=18        # higher quality
npx remotion render Main out/main.gif --codec=gif --scale=0.3 --every-nth-frame=2
npx remotion render Ad out/ad-square.mp4 --props='{"format":"square", ...}'
npx remotion render Main out/main.mp4 --gl=angle      # when using WebGL effects/3D
```

Review stills before the full render: they are 10× cheaper and catch 90% of problems.
Both scripts only use Remotion's own packages and its bundled ffmpeg (`npx remotion ffmpeg`).
That ffmpeg build is minimal (no `rawvideo` muxer, no `tile`/`fps`/`freezedetect` filters);
the scripts pipe raw frames via `image2pipe` and compose in Node — reuse `scripts/lib/media.mjs`
instead of assuming a full system ffmpeg exists.

### Programmatic (servers, queues, AI pipelines)

```ts
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const serveUrl = await bundle({entryPoint: path.resolve("src/index.ts")}); // once, reuse
for (const props of variants) {
  const composition = await selectComposition({serveUrl, id: "Ad", inputProps: props});
  await renderMedia({composition, serveUrl, codec: "h264", inputProps: props, outputLocation: `out/${props.id}.mp4`});
}
```

At scale: `@remotion/lambda` (AWS) or `@remotion/cloudrun` — follow the official docs.

## 9. Pitfalls

| Symptom | Cause / fix |
|---------|-------------|
| Flicker between frames | Non-deterministic value (Math.random, Date, CSS animation, R3F `useFrame`) |
| Image pops in late | Missing `premountFor`, or `<img>` instead of `<Img>` / `<CanvasImage>` |
| Font swaps mid-render | Font not loaded via `loadFont` / `@remotion/fonts` |
| Text jitters while counting | Missing `font-variant-numeric: tabular-nums` |
| Scene shows through another during transition | Scene has no background |
| Duration doesn't match audio | Hard-coded duration; use `calculateMetadata` |
| Effects render black/blank | WebGL not enabled: `--gl=angle` / `setChromiumOpenGlRenderer('angle')` |
| Shader transition invisible in Studio | Chrome flag `#canvas-draw-element` off (render is fine) |
| Version mismatch warning | All remotion packages + zod to the exact versions the CLI asks for |
| Slow renders | Heavy `filter: blur()` on large layers, too many motion-blur samples, unused font weights |
