# Art Direction — {Project name}

> Fill before animating. Keep it to one page. Every scene must be defensible against it.
> In autonomous runs, fill it with your assumptions and mark them `(assumed)`.

## Brief
- **Core message (one sentence):**
- **Audience:**
- **Platform / format / fps:** e.g. Instagram Reels · 1080×1920 · 30 fps
- **Duration:** from audio `__ s` (measured) / estimated `__ s` at 2.7 words/s
- **Final action wanted:** e.g. comment "MOTION", click "Teste grátis"
- **Constraints:** brand guide, legal copy, product UI, music license

## Concept
- **Feeling (2–3 adjectives):**
- **Visual metaphor:** e.g. "code is a blueprint"
- **Why it fits:**

## System
| Element | Decision |
|---------|----------|
| Palette | bg `#` · surface `#` · ink `#` · muted `#` · accent `#` · accent2 `#` (use: ) |
| Type | display: ____ (weights) · text: ____ · mono: ____ · scale [display, h1, h2, body, label] |
| Grid | margin __ px · __ columns · alignment: left-editorial / centered |
| Shapes | allowed primitives, stroke weights, radii |
| Materials & light | flat / paper / glass… · light direction · grain % |
| Camera | locked / drift / push · depth planes · real 3D yes/no |
| Motion personality | fast __ s · base __ s · slow __ s · stagger __ s · enter `ease.__` · exit `ease.__` · overshoot allowed? |
| Transition grammar | e.g. hard cut = new idea · wipe = before/after · match cut = transformation |
| Effect budget | allowed effects + max intensity; signature effect of this video |
| Sound | voice / music mood / SFX palette |

## Intensity curve
`hook ▇▇▇▆ · context ▅▅ · mechanism ▆▇ · payoff ▇▇▇ · CTA ▃▃ (calm, legible)`

## Anti-rules
- e.g. no gradients · no rotation on type · never center paragraphs · no particles

## Direction object (code)
```ts
export const direction: Direction = { /* mirror the table above */ };
```
