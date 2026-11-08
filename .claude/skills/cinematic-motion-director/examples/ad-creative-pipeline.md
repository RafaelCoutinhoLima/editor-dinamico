# Example — AI pipeline generating ad variants

A SaaS already uses an LLM to write ad copy and wants motion creatives rendered
automatically in several formats.

## Brief
- Product: AI tool that generates video ads. Goal: free-trial sign-ups.
- Platforms: Meta Reels + Feed, TikTok. Formats: 9:16, 4:5, 1:1.
- Volume: 20–50 variants per week. No human editor in the loop.

## Decisions
1. **Template, not free-form generation.** One `AdCreative` composition owns motion, timing,
   safe zones and layout per format. The LLM only fills JSON props.
2. **Schema contract** (zod) with limits: hook ≤ 60 chars, benefit ≤ 90, CTA ≤ 24,
   `format` enum, brand colors as strings, `proof` object.
3. **Structure:** Hook → Benefit → Proof → CTA. Duration computed from copy length in
   `calculateMetadata` (hook 1.8 s, benefit = words/3.2 + 0.8 s, proof 2.2 s, CTA 2.4 s).
4. **Direction from brand props** mapped onto Signal Noir defaults; accent used only for the
   hook emphasis word, the proof number and the CTA.
5. **Safe zones:** `useSafeArea("meta-reels")` on 9:16, `"feed"` elsewhere; `showGuides`
   prop for QA renders.

## LLM output (validated before render)
```json
{
  "format": "vertical",
  "hook": "Seu anúncio parece template?",
  "hookEmphasis": "template",
  "benefit": "Criativos em motion com direção de arte, gerados por IA em minutos.",
  "proof": { "value": 12, "suffix": "x", "label": "mais variações por semana" },
  "cta": "Teste grátis",
  "brand": { "name": "Sua Marca", "bg": "#0A0A0B", "ink": "#F4F1EA", "accent": "#FF4D1C" },
  "showGuides": false
}
```

## Render
```bash
npx remotion render AdCreative out/suamarca_trial_hpsc_hook01_9x16.mp4 --props=variant.json
```
Batch: bundle once, then `selectComposition` + `renderMedia` per variant (see
`references/remotion-implementation.md` §8).

## QA per batch
- Render one stress variant with every field at max length, in every format.
- `review-frames.mjs --comp AdCreative --props ... --count 6` with `showGuides: true`.
- Check frame 0 as thumbnail, CTA hold, contrast with the brand colors.

Working code: `showcase/cinematic-motion-director/src/AdCreative.tsx` (tested: 9:16 with
safe-zone guides and 1:1 with a light brand palette, October 2026).
