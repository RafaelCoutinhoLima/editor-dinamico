# Talking-Head Edits & Captions

For creator videos: a person talking to camera (A-roll) + captions + motion graphics on
top. Different job from a pure motion piece: **the face and the voice are the hero**; motion
supports, never competes. Verified with Remotion 4.0.535.

## 1. Pipeline

```
raw video ─► transcribe (whisper.cpp) ─► Caption[] JSON ─► review/fix text
         └─► detect pauses (silencedetect) ─► cut list
Remotion:   <Video> segments (trimBefore/trimAfter) + punch-ins + captions + motion overlays + SFX
```

### Quick start: official TikTok template

```bash
npx create-video@latest --yes --tiktok my-editor
cd my-editor && npm i
```

Before transcribing a non-English video, edit `whisper-config.mjs` — the default
`medium.en` model only understands English:

```js
export const WHISPER_MODEL = "medium"; // 1.5 GB; "small" (466 MB) to test; never ".en" for PT/ES
export const WHISPER_LANG = "pt";
```

Put the video in `public/`, run `node sub.mjs` (first run downloads whisper.cpp + model),
then `npm run dev`. The JSON next to the video holds the captions.

### Inside an existing project

`npx remotion add @remotion/install-whisper-cpp @remotion/captions` and follow the official
`remotion-captions` skill: `installWhisperCpp()`, `downloadWhisperModel()`, `transcribe()`,
`toCaptions()` → `Caption[]` (`{text, startMs, endMs, timestampMs, confidence}`).
Audio must be 16 kHz WAV: `npx remotion ffmpeg -i in.mp4 -ar 16000 out.wav`.

**Always review the transcript** before rendering: brand names, product names, numbers and
slang are where Whisper fails. Fix the JSON, don't re-time by hand.

## 2. Caption pages and styles

```ts
import {createTikTokStyleCaptions} from "@remotion/captions";
const {pages} = createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 800});
// page: {text, startMs, durationMs, tokens: [{text, fromMs, toMs}]}
```

`combineTokensWithinMilliseconds` controls words per page: ~400–800 ms → 1–3 words (punchy),
1200–2000 ms → full phrases (calmer). Highlight the active token by comparing the current
time (`frame / fps * 1000`) with `fromMs/toMs`.

Offer styles as separate compositions over the same video and captions, render a still of
each at the same second, and let the user choose before the full render:

| Style | Look | Best for |
|-------|------|----------|
| **Pill** | 1–3 words, uppercase, active word in accent, dark translucent pill | Energetic reels, ads |
| **Karaoke** | word by word, no background, heavy stroke/shadow for contrast | Fast talkers, music |
| **Box** | 1–2 lines, solid background, sentence case | Educational, calm, accessibility |
| **Editorial** | mixed weights/sizes, key word scaled up, follows the direction's type | Premium/brand content |

Caption rules:
- Size ≥ 56 px (1080 wide), weight 700–900, contrast ≥ 4.5:1 via background or stroke.
- 1–3 words per page for hooks, ≤ 2 lines ever. Break pages on pauses (`breakOnSilenceAfterMilliseconds`).
- Never cover eyes or mouth. Default band for 9:16 with a centered face: y ≈ 1100–1250 px
  (just above the bottom UI zone); move up when the face is low. Check with `SafeZoneGuide`.
- One emphasis treatment (accent color OR scale-up), used only on words that matter.
- Captions appear on the word, not before (±2 frames). Pop-in ≤ 4 frames; no long entrances.

## 3. Editing the A-roll

- **Always remove the breaths and dead air — before anything else.** Audible inhales and
  pauses between phrases make a talking head feel slow; creators expect them gone by default.
  Run `scripts/cut-breaths.py raw.mp4 --out cut.mov --speed 1.10 --verify` (energy-based:
  keeps only audio louder than speech level − 24 dB, collapses quiet stretches > 0.2 s,
  pads 0.05 s / 0.07 s, 8 ms fades so cuts don't click). It cuts video and audio together
  and writes `cut.timemap.json` (original time → new time).
  - **Never cut on Whisper word gaps.** Word timestamps are unreliable at phrase edges; a
    real edit lost the word "designers" that way. Cut on measured energy, then verify.
  - **Verify every time:** `--verify` re-transcribes before/after and fails on any run of
    missing words. Read the "possibly missing" list; single-word drift ("e", "o") is Whisper
    noise, two or more consecutive words is a real cut → lower `--thr` and re-run.
  - **Then speed up**, not before (`--speed`; 1.05–1.10 is natural for most creators —
    ask once, remember the answer). Breath-removal alone usually takes 12–18 % off.
  - **Re-time everything through the time map**: captions (re-transcribe the cut file, or map
    word times), scene/overlay cues, punch-ins, SFX hits and music sections. Write cues once
    on one timeline and convert with a single `M(t)` function — never hand-edit numbers.
- **Hide jump cuts** with punch-ins: alternate scale 1.0 / 1.12–1.18 on consecutive segments
  (hard switch on the cut, not animated), centered on the face.
- **Emphasis zooms:** slow push (1 → 1.06 over the sentence) on key statements; a fast punch
  (6–8 frames, `ease.out`) on the hook word.
- **Pacing:** something should change every 1.5–3 s (cut, punch-in, caption page, overlay).
  `rhythm-audit.mjs` measures this on the render.
- **Loudness:** voice around −14 LUFS integrated for social (`npx remotion ffmpeg … -af loudnorm`).

## 4. Motion on top of a talking head

| Layout | When |
|--------|------|
| **Top scene** — motion card in the upper ~40% (below the top safe band), face below | Explaining a concept while talking; the scene illustrates the sentence |
| **Split screen** — motion panel on top (≈ 1020 px), camera below (≈ 900 px), captions on the seam | Whole-video explainers; the face stays on screen the entire time |
| **Full-screen insert** — 1–3 s cutaway to a motion scene, back to face | Proof, demo, number, before/after |
| **Lower-third / label** — name, title, source | First appearance, citations |
| **Overlay elements** — arrows, highlights, icons near the face | Light emphasis; never more than one at a time |

Split-screen camera framing:
- **The whole head must be visible** — hair to chin, with air above the hair. Pick the crop
  from stills at 3–4 moments (people lean and move); size it from the face, not the frame.
- Crop at the panel's aspect (e.g. 1080 × 900 → crop width × width·900/1080 from the source);
  if the face still gets cut, make the camera panel taller rather than zooming in.
- Punch-in zooms anchor near the eyes (`transformOrigin ≈ 50% 30%`) so they never crop the top of the head.
- Low-res sources (WhatsApp, 576 px wide) look soft when upscaled: ask for the original file.

Rules:
- The overlay illustrates the exact words being said at that moment — derive timing from
  caption tokens (`fromMs`), not by eye.
- Match the direction (palette, type) so overlays feel designed, not stickered on.
- Inserts: hard cut in on a stressed word, hold ≥ read time, cut back on a pause.
- Keep the face visible ≥ 60% of the runtime in personality-driven content.

## 5. QA additions

- [ ] Breaths/pauses removed with `cut-breaths.py --verify`; no run of missing words
- [ ] All cues (captions, overlays, SFX, music) re-timed through the time map after the cut/speed-up
- [ ] Split screen: whole head visible in the camera panel at every review frame
- [ ] Transcript reviewed: names, brands, numbers correct
- [ ] Captions inside safe zone, never over eyes/mouth, readable on a phone
- [ ] No jump cut without a punch-in or insert to hide it
- [ ] Overlays sync to the spoken words (±2 frames)
- [ ] `rhythm-audit` shows no dead stretches outside intentional holds
