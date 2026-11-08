# Storyboard — {Project name}

> One row per scene. Times from the real audio when it exists. Each scene: ONE job, ONE hero move.
> Format: {1080×1920 · 30 fps} · Total: {__ s / __ frames}

## Overview

| # | Time (s) | Narrative job | Voice / on-screen text | Hero move | Out |
|---|----------|---------------|------------------------|-----------|-----|
| 1 | 0.0–2.8 | Hook: create curiosity | "E se eu te dissesse…" | monumental mask reveal + slow push-in | hard cut |
| 2 | | | | | |
| 3 | | | | | |

## Scene cards

### Scene 1 — {name} · {start}–{end} s · {frames} f
- **Job:** what the viewer must feel/understand here
- **Voice:** exact words + emphasis words in **bold**
- **On screen:** text (line breaks by meaning), elements
- **Composition:** layout on the grid, focal point, what is empty
- **Camera:** move, values (e.g. zoom 1 → 1.08, `ease.inOut`), depth planes
- **Motion:** entrance order with timings (e.g. label 0.1 s → line 1 0.3 s → line 2 0.5 s), curves
- **Hold:** read time (0.4 s + 0.3 s × words) → __ s
- **Transition out:** type + why (relationship to next scene)
- **Sound:** SFX/music accent at __ s
- **Kit / components:** e.g. `MaskReveal`, `Camera`, `GridReveal`

### Scene 2 — …

## Sync cues (seconds → `cues(fps, {...})`)
```ts
const cue = cues(fps, { hook: 0, problem: 0, reveal: 0, cta: 0 });
```
