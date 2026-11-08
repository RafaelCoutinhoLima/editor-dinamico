# Reference Library

Where the rules in this skill come from, and what each source contributes. Use references
to extract **principles** — composition, rhythm, materiality, movement — never to copy a
frame, a style frame or a studio's signature move.

Link check: 2026-10-13 (repertoire section: 2026-10-13, GitHub API) (✓ = responded; ⚠ = blocks automated requests, open in a browser).

## Studios and repertoire

| Source | Principles extracted |
|--------|----------------------|
| **BUCK** — Comfy Brand Refresh ✓ https://www.buck.co/work/comfy-brand-refresh · portfolio ✓ https://www.buck.co/work | Motion as a *system*: type, 3D objects, lines and shapes share one logic, so any new piece looks related. → `Direction` object, shape vocabulary, transition grammar in `art-direction.md`. |
| **Ordinary Folk** ✓ https://www.ordinaryfolk.co/work | Turning abstract ideas into concrete visual metaphors; rhythm and composition at the service of narrative; transitions that carry meaning. → "visual metaphor" step, match cuts, intensity curve. |
| **Motionographer** ✓ https://motionographer.com/ | Contemporary repertoire: discovering studios, styles and directions. → use to widen options during the Concept step, not to pick a style to clone. |
| **Art of the Title** ✓ https://www.artofthetitle.com/ | Title sequence craft (Saul Bass lineage onward): typography as the protagonist, graphic match cuts, economy of means. → kinetic typography and match-cut rules. |

## Craft and physics of motion

| Source | Principles extracted |
|--------|----------------------|
| **School of Motion** — Intro to the Graph Editor ✓ https://schoolofmotion.com/blog/intro-to-the-graph-editor-in-after-effects | Timing vs spacing, value/speed graphs, ease-in/out, anticipation and overshoot as curve shapes. → `motion-principles.md` §1–3, the ghost-dot spacing demo in the showcase. |
| **Adobe After Effects** — Keyframe interpolation ⚠ https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/animation-keyframes/keyframe-interpolation.html · Motion blur ⚠ https://helpx.adobe.com/after-effects/using/motion-blur.html | Linear vs Bezier vs hold interpolation, spatial vs temporal interpolation, shutter angle. → kit `ease` table (Bezier values), hold frames, motion-blur guidance. |
| **The Illusion of Life** (Frank Thomas & Ollie Johnston, 1981) — the 12 principles of animation | Anticipation, follow-through, overlapping action, arcs, secondary action, timing, exaggeration. → `motion-principles.md` §3. |
| **easings.net** ✓ https://easings.net/ | Visual reference for standard easing families and their cubic-bezier values. |
| **Josef Müller-Brockmann — Grid Systems in Graphic Design** | Grid-based layout, alignment, typographic hierarchy. → grid rules in `art-direction.md`, `GridReveal`. |

## Technical (code-driven video)

| Source | Contribution |
|--------|--------------|
| Remotion — The fundamentals ✓ https://www.remotion.dev/docs/the-fundamentals | Video = function of frame; compositions, sequences, determinism. |
| Remotion — Transitions ✓ https://www.remotion.dev/docs/transitioning | `TransitionSeries`, timings, overlays, rules. Presentation list verified from the 4.0.535 package exports. |
| Remotion — Effects ✓ https://www.remotion.dev/docs/effects | `@remotion/effects`, supported components, WebGL requirement. |
| Remotion — Easing ✓ https://www.remotion.dev/docs/easing | `Easing.bezier`, `Easing.spring`. |
| Remotion — Motion blur ✓ https://www.remotion.dev/docs/motion-blur | `HtmlInCanvasMotionBlur`, `CameraMotionBlur`, `Trail`. |
| Remotion — Three ✓ https://www.remotion.dev/docs/three | `ThreeCanvas`, frame-driven R3F. |
| Remotion official agent skills ✓ https://github.com/remotion-dev/skills | API-level best practices (inline interpolations, premounting, media components, fonts, rendering). This skill defers to them for API specifics. |
| Agent Skills format ✓ https://agentskills.io | `SKILL.md` format shared by Claude Code, Codex and other agents. |

## Prompt repertoire

| Source | Contribution |
|--------|--------------|
| awesome-opus5-5-videos ✓ https://github.com/yihui-dev/awesome-opus5-5-videos (MIT list; the videos belong to their authors) | Analysed 2026-10-16: 703 entries (369 motion, 117 3D, 116 explainer, 101 interactive); 207 partial; median complete prompt = 35 words; 79 distinct prompts ≥ 100 words were read in full and distilled into `scene-recipes.md` (recipes, field numbers, default prohibitions, gotchas — credited by slug). Strongest briefs: twoclipping-000267, twoclipping-496100, flxrnc-251921, everestchris6-399895 (critic loop), brainextends-606193, gdgtify-989608. Earlier analysis: code-animation videos with the prompts behind them (`data/videos.json`, `prompts/*.md`). Lesson: one-line prompts give generic showreels; the strong ones are *director prompts* — real inputs, a direction paragraph, a prohibition list, a timeline with exact on-screen text and a stills check before delivery. → `templates/director-brief.md`. Use the prompts as structure references, with credit; never reuse other people's brands or footage. Many entries are partial (`prompt_partial: true`) — skip those. |
| Remotion TikTok template ✓ https://github.com/remotion-dev/template-tiktok | Whisper.cpp transcription + TikTok-style captions. → `talking-head-captions.md`. |
| HyperFrames ✓ https://github.com/heygen-com/hyperframes (Apache-2.0) | Alternative engine: write HTML, render video, built for agents. Consider when a project is HTML-first; this skill's direction and review rules apply unchanged. |

## Film-in-code repositories (checked 2026-10-25)

Use for *method*, not assets. License noted because it decides what can be reused in paid work.

| Source | License | Method extracted |
|--------|---------|------------------|
| Lemo-Opuscar ✓ https://github.com/lemomo-ai/lemo-opuscar | see repo | Named style library (59 styles), each = style prompt + demo; agent directs, scores, narrates and mixes; custom style derived from an existing one. → `style-library.md` |
| 15 Motion Design Styles ✓ https://github.com/Vincentwei1021/mg-styles-15 | see repo | Style prompt split into *Signature features* (fixed) vs *Creative seed* (per client); music generated in code from instrument samples. → style-prompt structure, `synth-score.py` idea |
| ClaudeAnimationBase ✓ https://github.com/JohnHeibel/ClaudeAnimationBase | MIT (code); the Clawd mascot is Anthropic's | Character rig with emotions, animation guide, storyboard → shot by shot → own contact sheets; GPU cost of painterly fills. → `character-animation.md` |
| pdoom-video ✓ https://github.com/mexicat/pdoom-video | MIT (code only; song, lyrics and timings belong to their authors) | Word-level lyric sync, 17 scenes, 60 fps, timing analysis tools; heavy 4K renders. → `lyric-and-word-sync.md` |
| PDoomVideo ✓ https://github.com/JohnHeibel/PDoomVideo | no license (study only) | Painterly cartoon per verse, subagent guide written by the model itself. |
| Opus Video Prompts ✓ https://github.com/joeseesun/opus-video-prompts | see repo | 18 full prompts + 54 cases across 9 tech paths (Canvas, p5, Three, Remotion, Manim, Blender…). |
| awesome-claude-5-5-videos ✓ https://github.com/athemeroy/awesome-claude-5-5-videos | see repo | 424 posts with cost/method analysis by model. |
| claude-video-effects ✓ https://github.com/Vibha-Ramprakash/claude-video-effects (checked 2026-10-26) | MIT (models: YuNet MIT, MediaPipe selfie segmenter Apache-2.0) | 42 talking-head effects in Python/OpenCV: person mask + face track so graphics sit behind the head, never on the face; check stills mid-effect before rendering. → `talking-head-effects.md`, `person-matte.py`, `depth.tsx` (rewritten for Remotion) |
| Effect-showcase reels (Instagram, 2026-10: a 17-effect list, a 36-effect "/effects" demo) | study only | Numbered-list format with phone-mockup demos ~0.75 s each; command → dot-matrix processing → result format; comment CTA. → `talking-head-effects.md` §3 |
| earshot ✓ https://github.com/Leonxlnx/earshot (0.4.0) | MIT | Ears for agents: 252 designed SFX as code with an audit, a launch kit with measured offsets / bed levels / run gaps from pro clips, the 7-film launch-sound playbook, `critique` / `timeline` / `sheet`. → `sound-design.md`, `scripts/sfx-earshot.py` |
| Guide "8 repositórios grátis pra fazer filme com o Claude Code" (fabiano.app, 2026-10) | — | Named cuts with times, storyboard stop, one-fix review loop, 6 pre-delivery checks, license awareness, start with 15–30 s. → SKILL.md workflow, `quality-checklist.md`, `prompts-pt.md` |

## Ads

| Source | Contribution |
|--------|--------------|
| TikTok Creative Center ✓ https://ads.tiktok.com/business/creativecenter | Trending formats, top ads, native creative patterns. |
| Meta Ads Guide & Ads Manager safe-zone preview | Placement specs and safe zones. Values in `ad-creatives.md` are conservative compilations; confirm in Ads Manager before launch. |

## How to use this library during a project

1. In the Concept step, browse 2–3 sources relevant to the brief's tone.
2. Write down *principles* you want ("type as protagonist", "everything snaps to a grid",
   "a single warm accent cutting through dark"), not frames.
3. Combine them with the project's own metaphor. If the result could be mistaken for a
   specific studio's piece, push it further away.
