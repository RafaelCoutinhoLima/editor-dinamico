# Example — Reel: "Motion sem After Effects"

A creator explains that an AI agent can write motion design as code. Narration in
Portuguese (PT-BR), ~60–75 s. Shows how a script becomes direction + storyboard.
The rendered 15 s teaser of this concept is `showcase/cinematic-motion-director` in the
skills repository.

## A — Analysis
- **Audience:** creators, designers and devs curious about AI video.
- **Core message:** "With the right references and direction, an agent writes professional motion as code."
- **Tone:** confident, a bit provocative, technical but accessible.
- **Platform:** Instagram Reels / TikTok · 1080×1920 · 30 fps.
- **Action:** comment "MOTION" to receive the skill.

## B — Timing
Script ≈ 170–200 words → ~63–74 s at 2.7 words/s. **Use the real voiceover duration.**
Do not compress into 15 s; "15 seconds" appears inside the narration as an example only.
Emphasis words: *After Effects*, *PowerPoint de 2009*, *referências certas*, *código*,
*quadro a quadro*, *mais suave*, *MOTION*.

## C — Concept
- **Feeling:** precise · surprising · effortless
- **Metaphor:** "code is a blueprint that renders into film" — grid, hairlines, coordinates,
  things snapping into place, then resolving into finished cinematic frames.
- **Direction:** Signal Noir (dark, Inter Tight 800, JetBrains Mono labels, one hot orange
  accent `#FF4D1C`, acid green `#C8FF3D` reserved for code). Grain 6%, vignette, faint grid.
- **Transition grammar:** hard cut = new idea / joke · wipe = before→after · match cut on the
  orange dot = transformation · slide up = next step in the pipeline.
- **Anti-rules:** no glow, no particles, no gradients, no rotation on sentences.

## D — Storyboard (times are placeholders until the VO is measured)

| # | Narration (excerpt) | Narrative job | Direction |
|---|---------------------|---------------|-----------|
| 1 | "E se eu te dissesse…" | Hook, curiosity | Abrupt type entrance (`WordStagger` mask), slow push-in 1→1.08, minimal composition, grid at 8% |
| 2 | "…sem nem abrir o After Effects?" | The provocation | "After Effects" in monumental scale, accent color; ink strike-through draws across on "sem"; spatial cut revealing there is no timeline |
| 3 | "…parecia um PowerPoint de 2009" | Comic contrast | Deliberately bad: linear motion, default-looking type, hard stop, a beat of visual silence → hard cut to the same layout with premium easing (ghost-dot spacing comparison) |
| 4 | "…as referências certas" | Method | `GridReveal` builds; four cells resolve into type sample, palette, rhythm bars, easing curve — distinct elements that connect with `DrawLine` |
| 5 | "Ele escreve a animação como código" | Mechanism | Text and shapes decompose into coordinates and lines; `Scramble` in mono acid green; camera tilts down the structure |
| 6 | "Pedido, código, render, vídeo" | Process | Four stages on a vertical line; each lands as the line reaches it (overshoot on the dot only); slide-up transition from previous scene |
| 7 | "…é renderizado quadro a quadro" | Technical proof | `CharCascade` "QUADRO A QUADRO", film strip at constant (linear, intentional) speed, live frame counter |
| 8 | "Deixa essa transição mais suave" | Iteration demo | Same composition twice: hard linear → refined `ease.inOut` + motion blur; label "antes / depois" |
| 9 | "Comenta MOTION" | CTA | Locked camera, fade in, "MOTION" `TrackingIn` + `Highlight` in accent, hold ≥ 2 s, URL small in mono |

## E — Build notes
- `direction.ts` from Signal Noir with the project fonts.
- One scene component per row; cue points from the VO transcript via `cues(fps, {...})`.
- Music: minimal pulse at ~100 BPM, ducked under voice; SFX: soft click on each pipeline
  stage, single low hit on the CTA.

## F — Review focus
Hold frames of scenes 2, 6 and 9 (unfinished animations?), safe zone on the CTA, the
"2009" contrast reads as intentional (not as a bug), legibility of mono labels on phones.
