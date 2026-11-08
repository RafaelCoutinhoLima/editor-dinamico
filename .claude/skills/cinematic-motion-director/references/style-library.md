# Style Library

A style is a reusable *film language* — palette, type, motion signature, transition grammar,
sound — that can be pointed at any subject. Studios sell "the same look, a new client"; this
file lets the agent do that without the result looking like a template.

## 1. Style prompt = Signature features + Creative seed + Output spec

Keep these three blocks separate in every brief (the structure the best open-source "film in
code" prompt libraries use):

```text
## Signature features   (fixed — this IS the style; never edit per client)
palette, type, grid, motion signature, transition grammar, texture, sound palette, prohibitions

## Creative seed        (changes per client/video — the ONLY part a new job edits)
subject / brand name, one-line promise, real assets, accent hex, the main moment and its time,
exact on-screen text

## Output spec          (numbers only)
1080x1920 · 30 fps · 10.0 s · MP4 (+ 1920x1080 variant if asked) · loudness -14 LUFS
```

Rule: to make a vignette for a new client, copy a style file and replace **only** the Creative
seed. If you feel the need to edit Signature features, you are creating a new style — save it
under a new name (§4).

## 2. How to pick

| The piece is… | Start from |
|---|---|
| a true story / case with a turn (incident, crash, comeback) | Red Thread Noir |
| tech/AI news, explainer for a smart audience, white & warm | Claude Paper |
| a list, "signs you are…", quiz, checklist hook for follows | Terminal Checklist |
| business news reacting to a headline (acquisition, round, launch) | Business News Card |
| product launch, keynote energy, few words, big type | Dark Tech Keynote |
| numbers with sources, maps, charts, "explain like a documentary" | Data Documentary |
| channel/podcast/event opener, 6–10 s, logo hit | Chrome Vignette |
| vertical show-like captions, pop words, auditorium energy | Variety Captions |
| music video where every word is on the beat | Kinetic Lyric (see `lyric-and-word-sync.md`) |
| a character acting a small story | Ink Character (see `character-animation.md`) |
| founder/creator talking + motion panel | Split Screen Studio |
| collage, paper, tactile editorial | Paper Collage |

Two styles max per piece; the second only as a contrast beat (e.g. Claude Paper calm section
inside a Red Thread Noir story).

## 3. The styles

Each entry: signature features first; kit components in `code`. Numbers are defaults — the
Creative seed may override the accent hex and nothing else.

### Red Thread Noir
- **Use:** stories with stakes and a turn. Proven on a 50 s "bug that cost US$ 460M" reel.
- **Palette:** ink `#0B0B0C`, paper `#F4F1EA` (calm beats), alarm `#FF3B30`, ticker `#2FD27A`, amber `#FFB020`.
- **Type:** grotesk 700–800, tight (-0.04 em) for numbers; mono for data labels.
- **Motion signature:** one red line (price/thread) is present in every scene and *becomes* the next scene's object (strike-through, wire, chart). `DrawLine`, `CountUp`, `MaskReveal`.
- **Transitions:** hard cuts on SFX hits; one hard cut to silence (paper) at the lesson.
- **Sound:** ticking clock in the build, sub-drop on the punchline, silence for the lesson.
- **Prohibited:** glitch, neon glow, particles, camera shake.

### Claude Paper
- **Use:** AI/tech news, explainers, calm authority. White background.
- **Palette:** `#FFFFFF` / ivory `#FAF9F5`, ink `#141413`, clay `#D97757`, olive `#788C5D`, kraft `#D4A27F`.
- **Type:** grotesk 640–800 headlines, mono 700 kickers with a clay dot.
- **Motion signature:** "scattered dots that connect" — data islands, hub-and-spoke links drawing, people-icon rows filling. Cards rise 50 px with `ease.out`.
- **Transitions:** whip-in for real photos (0.18 s, blur ≤ 16 px), punch-ins ≤ 3.5 %.
- **Sound:** warm synth bed, minor → major lift at the reveal.
- **Prohibited:** dark backgrounds, gradients on buttons, emoji.

### Terminal Checklist
- **Use:** "signs you are…/checklist" hooks built to win followers. Proven 30 s, 17 shots.
- **Palette:** `#0E0E10`, white `#F7F5F0`, check green `#2FD27A`, clay `#D97757`.
- **Motion signature:** persistent HUD `CHECKLIST · n/9` with pips; each item = 1 shot (1.2–2.6 s) with real footage/photo and a ✓ ticking on the exact word; ends with a 9/9 summary + follow button press.
- **Sound:** mouse click on every cut (soft), tick on every ✓. No music by default.

### Business News Card
- **Use:** reacting to a headline. Proven 84 s acquisition reel.
- **Opener (mandatory):** real clipping of the article headline + date + source, then the question in huge type ("O iFood comprou a Caju?") with the brands' real images.
- **Palette:** white editorial + the two brands' real colors sampled from official images (never guessed).
- **Motion signature:** big counters per company → circles merging into the total; strike "not X" → "it's Y"; numbered action steps that light up on the voice.
- **Credits:** clipping/source credited on screen; "ilustrativo" label on any non-sourced bar.

### Dark Tech Keynote
- **Palette:** `#05060A`, white, one electric accent from the brand.
- **Type:** 900 weight, 180–260 px words, one word per beat.
- **Motion signature:** `TrackingIn` titles, product UI in a floating device with slow 2.5D push, benefits one per downbeat (`beat-map.mjs` first).
- **Sound:** 120 BPM electronic, drop on the product reveal.
- **Prohibited:** stock icons, more than 4 words on screen at once.

### Data Documentary
- **Rule:** every number shows its **source on screen for ≥ 2 s** when it appears; list the numbers and sources to the user before building.
- **Palette:** off-white `#F2EFE8`, ink, one data accent, one comparison grey.
- **Motion signature:** charts that draw from the axis, maps with pins, counters that land with a tick. Hook = the most surprising number in the first 3 s.
- **Pace:** narration ~150 wpm; one idea per scene.

### Chrome Vignette
- **Use:** 6–10 s brand opener. Main moment at 60–75 % of the length (title hits with the strongest chord).
- **Motion signature:** title in chrome/metal gradient (CSS gradients + highlight sweep), camera dolly through 2–3 depth layers, logo lock-up held ≥ 1 s.
- **Delivery:** always both 1920x1080 and 1080x1920 (§5).

### Variety Captions
- **Use:** vertical show/podcast segment openers.
- **Motion signature:** 3 short phrases popping with overshoot, colored caption boxes rotating ±3°, auditorium SFX (clap, whoosh, ding) on each phrase, title held 1 s at the end.

### Split Screen Studio
- Motion panel top (≈ 1020 px), camera bottom (≈ 900 px), captions on the seam. Whole head always visible (see `talking-head-captions.md`).

### Paper Collage
- Torn-paper masks, cut-out photos with white borders and drop shadows, hand-written labels, stop-motion feel at 12 fps for the collage layer only (`Math.floor(frame/2)*2`).

### Kinetic Lyric · Ink Character
- See `lyric-and-word-sync.md` and `character-animation.md`.

## 4. Saving a custom style (style memory)

When a user approves a look, save it so the next video starts from it:

```
styles/<style-name>.md      # Signature features + 2 approved stills + the direction.ts values
```

Next time: "use the style `<name>` with this Creative seed". Keep the client's brand values
out of the style file (they belong to the seed), so one style serves many clients.

## 5. Format variants of the same film

Build compositions from one `direction` + one cue map and a `format` prop (`formats.tsx`).
Re-layout per format with zones (`spacing-and-layout.md`) — never just crop a 16:9 render
into 9:16. Run the per-shot spacing pass for **each** format.
