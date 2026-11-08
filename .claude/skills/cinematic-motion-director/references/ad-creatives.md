# Ad Creatives & AI Pipelines

For performance ads (Meta, TikTok, YouTube Shorts, LinkedIn) and for products that generate
video creatives automatically. The goal is different from a brand film: stop the scroll,
land one message, drive one action — at scale, in many variants, without losing craft.

## 1. Principles that change for ads

- **The first 1–2 seconds are the ad.** Open on the hook already in motion — no logo intro,
  no fade from black, no "Hi guys". The first frame must be a strong still on its own
  (it is often the thumbnail).
- **Sound-off first.** The message must read with no audio. On-screen text carries it;
  voice and music add energy.
- **One idea per screen.** Hook ≤ 7 words. Benefit ≤ 12 words. One number per proof screen.
- **Faster rhythm, same craft.** Shorter durations (base ~0.4 s), more cuts, but every move
  still has an easing intent and every screen still holds long enough to read.
- **Brand early, CTA clear.** Brand visible by ~3 s (logo, color or product). CTA end card
  holds ≥ 1.5–2 s, with the action as a verb ("Teste grátis", "Baixe agora").
- **Real inputs only.** The template never invents features, numbers, testimonials or
  logos. If the pipeline has no proof value, the proof screen is skipped — not filled with a
  plausible number.
- **Native beats polished-generic.** Creatives that feel made for the platform outperform
  TV-style spots. Premium motion ≠ corporate.

## 2. Structures (pick one per variant)

| Structure | Beats | Length |
|-----------|-------|--------|
| Hook → Problem → Solution → Proof → CTA | the default | 15–30 s |
| Bold claim → Demo → CTA | product/UI demos | 10–20 s |
| Before / After | split or wipe; same layout, changed outcome | 6–15 s |
| Listicle ("3 motivos…") | numbered beats, each 2–3 s | 15–25 s |
| Offer | price/discount as hero, urgency, CTA | 6–10 s |
| Testimonial overlay | real quote or UGC footage + kinetic captions + proof | 15–30 s |
| Question hook | question → tension → answer reveal → CTA | 10–20 s |

## 3. Formats and safe zones

| Format | Size | Use |
|--------|------|-----|
| 9:16 | 1080×1920 | Reels, Stories, TikTok, Shorts — primary |
| 4:5 | 1080×1350 | Feed (Meta) |
| 1:1 | 1080×1080 | Feed, marketplaces |
| 16:9 | 1920×1080 | YouTube in-stream, web |

Safe zones for 9:16 (keep text, logos and CTA out of these bands). Conservative values
compiled from platform guides in 2026; platforms change overlays often — verify with
Meta's / TikTok's safe-zone preview in Ads Manager before launch:

| Platform | Top | Bottom | Sides |
|----------|-----|--------|-------|
| Meta Reels/Stories | 14% (~270 px) | 35% (~670 px) | 6% (~65 px) |
| TikTok | ~9% | ~30% | right ~12% (action buttons), left ~6% |
| YouTube Shorts | ~10% | ~25% | right ~12% |

The kit encodes these as `SAFE_ZONES`; use `useSafeArea(zone)` for padding and
`<SafeZoneGuide zone>` (behind a `showGuides` prop) during review.

Design each format separately — don't just letterbox 9:16 into 1:1. Recompose: in square,
type is smaller relative to width, layouts become side-by-side, holds can be shorter.

## 4. Text and legibility for ads

- Minimum on 1080 wide: 56 px for any message text, 44 px for secondary, 30 px for legal.
- Max ~2 lines per screen for hooks; never more than ~12 words on screen.
- Contrast ≥ 4.5:1 against everything behind the text, including moving footage (use a
  solid panel, a scrim or darkened footage — not a drop shadow).
- Numbers: tabular figures, unit as part of the visual (`12x`, `R$ 49`), hold ≥ 1 s.

## 5. Template system (the right architecture for AI-generated creatives)

Don't let an LLM write fresh JSX for every ad in production. Split responsibilities:

```
LLM / user / CMS  ──►  JSON props (copy, assets, brand, format, structure)
                          │  validated by zod
                          ▼
               Remotion template (owns motion, timing rules, safe zones, quality)
                          │  calculateMetadata → size & duration from props
                          ▼
                  renderMedia → MP4 per variant
```

- **Schema = contract.** Define a zod schema with explicit limits (`max(60)` on the hook,
  enums for formats/structures, color strings). Reject or truncate before rendering.
- **Timing derived from content.** Duration per screen computed from word count
  (`estimateSpeechSeconds`) with min/max clamps; total duration via `calculateMetadata`.
- **Direction as props.** Brand palette and font choice come in through props, mapped onto
  the template's `Direction`. Validate contrast; fall back to safe ink/bg when it fails.
- **Layout adapts to format.** Read `width`/`height`, scale type by `width / 1080`, choose
  layout per aspect ratio, apply the platform safe area.
- **Assets.** Remote URLs or `staticFile`. Use `premountFor`; check images are reachable
  before batch rendering. Product screenshots go into device frames or clean cards.
- **Determinism.** Same props → same video. Seed any randomness with the variant id.

A complete working example (schema, `calculateMetadata`, safe areas, 4 formats) lives in the
skills repository: `showcase/cinematic-motion-director/src/AdCreative.tsx`.

When this skill runs INSIDE an existing pipeline project: read the existing schema and
compositions first, improve motion/timing/layout inside the template, keep the props
contract backward compatible (add optional fields with defaults; don't rename), and render
a sample per format to prove nothing broke.

## 6. Variant strategy

Change one variable at a time so results are learnable:

| Axis | Examples |
|------|----------|
| Hook | question / bold claim / number / pain point / "POV:" |
| Visual opening | type-only / product UI / footage / face |
| Structure | from section 2 |
| Proof | number / testimonial / logo wall / demo |
| CTA | verb, offer, urgency |
| Format | 9:16, 4:5, 1:1 |

Name outputs so the ads manager stays readable:
`{brand}_{campaign}_{structure}_{hookId}_{format}_{yyyymmdd}.mp4`.

Batch rendering: bundle once, loop `selectComposition` + `renderMedia` per variant
(see `remotion-implementation.md` §8). For large batches use `@remotion/lambda`.

## 7. Delivery specs

- MP4, H.264, yuv420p, AAC audio, 30 fps (keep source fps), CRF ~18–23.
- Keep files well under platform limits; 15–30 s at 1080p is usually 3–15 MB.
- Include a silent-safe version (all info on screen). Optional burned-in captions.
- Export a thumbnail still from the strongest early frame (`npx remotion still`).

## 8. Ad QA (in addition to `templates/quality-checklist.md`)

- [ ] Frame 0 works as a thumbnail; hook readable within 1 s
- [ ] Message understandable with sound off
- [ ] Brand visible by ~3 s; CTA end card ≥ 1.5 s
- [ ] Text and CTA inside the platform safe zone in EVERY format rendered
- [ ] No claim the brand can't prove; required legal copy present and legible
- [ ] Props at their max length still fit (render a stress-test variant with the longest copy)
- [ ] Brand colors pass contrast; fallback applied when they don't
