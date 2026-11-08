# Art Direction

Direction is the set of decisions that makes 40 scenes look like one film. Write it down
before animating (`templates/art-direction.md`) and express it in code as a `Direction`
object, so every scene reads from the same source.

## 1. From brief to concept

1. **Core message in one sentence.** If you can't write it, you can't direct it.
2. **Feeling.** Two or three adjectives the viewer should feel (e.g. "precise, surprising,
   effortless"). Every choice below must be defensible against them.
3. **Visual metaphor.** One idea the whole video is built from. Examples:
   - "Code is a blueprint" → grid, thin lines, measurements, things snapping into place.
   - "Signal through noise" → grain, scrambles resolving, a single accent cutting through dark.
   - "Paper and ink" → warm off-white, serif, roughened edges, ink-like masks.
   - "Instrument panel" → mono labels, counters, gauges, precise linear tickers.
   A metaphor gives you a shape vocabulary, a transition grammar and a reason to say no.
4. **Constraints.** Brand guide, platform, legal copy, product UI that must appear, music.

Respect the brand when one exists: its colors, typefaces and tone override every default
here. Your job is to make the brand move, not to replace it.

## 2. The system to define

| Element | Decide |
|---------|--------|
| Palette | bg, surface, ink, muted, 1 accent (+1 optional). 60/30/10 split. Text contrast ≥ 4.5:1 |
| Type | display + text (+ mono for labels/data). Max 2 families + mono. Size ladder, tracking |
| Grid | margins, columns, alignment rule (left-aligned editorial vs centered statement) |
| Shapes | the 2–3 primitives allowed (circle, hairline, rounded rect, arrow…), stroke weights, radii |
| Materials & light | flat / paper / glass / metal / gradient; light direction; grain amount |
| Camera | locked / drifting / pushing; depth planes used; whether real 3D is allowed |
| Motion personality | durations (fast/base/slow), default enter/exit curves, stagger, overshoot allowed? |
| Transition grammar | the 2–3 transitions allowed and what each means in this video |
| Intensity curve | where the video peaks, where it breathes |
| Effect budget | which effects exist in this world and their max intensity |

Write anti-rules too: "no gradients", "never center paragraphs", "no rotation on type".

## 3. Starter directions

Starting points to adapt — not presets to ship. All fonts are available in
`@remotion/google-fonts`.

### Signal Noir — tech, AI, developer, creator education (kit default `signalNoir`)
- Palette: `#0A0A0B` bg, `#141416` surface, `#F4F1EA` ink, `#8A8780` muted, `#FF4D1C` accent, `#C8FF3D` accent2 (data/code only)
- Type: Inter Tight 800/600 display, Inter text, JetBrains Mono labels
- Motion: decisive `out` entrances, `snap` whips, slow push-ins on holds; overshoot rare
- Transitions: hard cuts, wipes for before/after, match cuts on the accent dot
- Texture: grain 5–7%, vignette, faint grid

### Editorial Paper — culture, education, storytelling, premium consumer
- Palette: `#F2EEE6` paper, `#E6DFD3` surface, `#161412` ink, `#6E675E` muted, `#C2361F` accent
- Type: Instrument Serif or Fraunces display (italic for emphasis), DM Sans text
- Motion: slower (base 0.8 s), `outSoft`, mask reveals by line, gentle lateral dollies
- Transitions: cuts and wipes that behave like turning pages; `bookFlip` sparingly
- Texture: `paper` effect or subtle grain, roughened image edges

### Swiss Grid — corporate, finance, B2B, data
- Palette: `#FFFFFF`, `#F1F1F1`, `#111111`, `#7A7A7A`, accent `#E30613` or `#0047FF`
- Type: Inter Tight / Geist, big numbers, strict left alignment, visible grid
- Motion: precise, `inOut` travels, elements snap to columns, `CountUp`s, almost no overshoot
- Transitions: slides along the grid axis, hard cuts
- Texture: none. Precision is the texture.

### Kinetic Brutal — hype, launches, sport, music, Gen Z ads
- Palette: `#000000` / `#FFFFFF` + one loud accent (`#D4FF00`, `#FF2D55`)
- Type: Anton / Archivo Black / Unbounded, full-bleed words, extreme scale contrast
- Motion: short durations (fast 0.2 s), `snap`, hard cuts on every beat, scale punches
- Transitions: cuts, push-cuts with flash, whips; `crossZoom` once at the peak
- Texture: chromatic aberration on impacts only, high-contrast footage

### Soft Product — consumer apps, wellness, fintech for everyone
- Palette: `#F6F4FF` bg, `#FFFFFF` cards, `#1D1B2F` ink, pastel accents (`#7B61FF`, `#FFB86B`)
- Type: Manrope / Outfit / DM Sans, rounded, friendly sizes
- Motion: springs (`ease.spring`, occasional `bouncy`), floating UI cards with parallax, soft shadows
- Transitions: `blurSlide`, scale-through-card, fades
- 3D: soft clay-like objects if budget allows (`@remotion/three`)

### Quiet Luxury — fashion, real estate, high-end services
- Palette: `#0E0D0B` or `#EFEAE2`, ink in warm neutrals, accent `#B08D57` used like jewelry
- Type: Cormorant Garamond / Playfair Display display, wide-tracked small caps labels
- Motion: slow (base 1.0–1.4 s), `outSoft`, long holds, tracking-in titles, slow push-ins
- Transitions: long fades, slow masks; never flashy
- Texture: subtle grain, real footage graded warm

## 4. Composition rules

- Pick a dominant alignment per video (left-editorial or centered-statement) and keep it.
- Use the grid for every element; things snap, not float.
- Negative space is a hierarchy tool: the most important element gets the most space.
- One focal point per frame. If two things compete, one waits.
- Rule of thirds for subjects; optical center (slightly above middle) for statements.
- Vertical video: content lives in the middle ~60% height; keep top 14% and bottom 35%
  clear of critical content for Reels/TikTok UI (see `ad-creatives.md`).
- Balance dark frames with one bright element; balance busy frames with one empty quadrant.

## 5. Anti-patterns (instant "template" look)

- Gradient on everything; purple-to-blue "tech" gradients by default.
- Glassmorphism cards floating with no light logic.
- Five fonts; centered everything; text with drop shadows for legibility instead of layout.
- Particles as wallpaper. Lens flares without a light.
- Every element bouncing; every cut a different transition.
- Stock-y emoji/icons mixed with premium type.
- Corporate slide layouts: title top-left, three bullets, logo bottom-right.

## 6. Originality

Study references for principles (see `reference-library.md`), never to copy a frame,
a style frame or a signature move of a studio or artist. Combine principles with the
project's own metaphor to produce something specific to this brief.
