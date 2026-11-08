# Voiceover-Driven Edits & Real Footage

Mode E: the user brings a finished narration (ElevenLabs or any VO) and wants a complete
video built on it — motion scenes, B-roll from real videos (YouTube or their own files),
sound bites with the original audio, captions and credits. Verified with Remotion 4.0.535
and yt-dlp 2026.08.19.

```
voice.mp3 ──► voice-map.mjs ──► voice.json (words, phrases, pauses)
                                      │
topic ──► footage.mjs search ─► fetch / import ─► transcript.json ─► moments ─► clip (--match voice)
                                      │                                   │
                                      └────────► edit.json (EDIT PLAN) ◄──┘
                                                      │
                                   EditTimeline (motion-kit/edit.tsx) ──► render ──► audits
```

## 1. Rights first (non-negotiable)

Downloading from YouTube is restricted by YouTube's Terms of Service, and footage is
copyrighted unless its owner says otherwise. The pipeline therefore:

- **Defaults to Creative Commons.** `footage.mjs search --cc` filters YouTube's "Creative
  Commons" results; `fetch` refuses anything whose `license` isn't CC unless the user gives
  a `--rights "<reason>"` (own channel, written permission, licensed).
- **Records attribution** for every source (`manifest.json`) and shows a "Fonte: …" tag on
  screen during B-roll and bites; `footage.mjs credits` produces the description credits.
  CC BY requires attribution — never drop it.
- **Keeps clips short and purposeful**: B-roll 1.5–4 s, sound bites ≤ ~10 s, transformed by
  the edit (crop, captions, commentary). Never re-upload someone's video as the main content.
- **Never invents** what a source said: sound bites use the source's real words, and the
  narration must not put words in the source's mouth.
- **Doesn't fight anti-bot checks.** If YouTube asks the network to sign in, stop and use an
  alternative: the user's own file via `footage.mjs import` (YouTube Studio lets owners
  download their uploads), licensed/CC files the user already has, Wikimedia Commons /
  Pexels / Pixabay downloads, or retry later from another network. Never bypass the check.

Tell the user in one line what license each clip has and that the final responsibility for
publishing is theirs.

## 2. The voiceover

Best → worst inputs (all handled by `scripts/voice-map.mjs`):

| Input | How the user gets it | Command |
|-------|----------------------|---------|
| ElevenLabs **TTS with timestamps** | API `POST /v1/text-to-speech/{voice_id}/with-timestamps` → JSON with `audio_base64` + `alignment` (per-character times) | `--alignment vo.alignment.json` |
| ElevenLabs **Speech-to-Text** / OpenAI `verbose_json` / Remotion `Caption[]` | transcribe the MP3 they already have | `--transcript vo.json` |
| MP3 + the **script text** | they exported only the MP3 from the ElevenLabs website | `--script roteiro.txt` (aligned on the audio's pauses; phrase-accurate) |
| MP3 only | nothing else available | `--whisper --lang pt --model small` (local whisper.cpp; downloads ~466 MB once) |

The output `voice.json` has `words`, `phrases` (sentence/pause boundaries) and `pauses`.
It drives everything: scene changes, kinetic words appearing as they're spoken, captions.

Notes:
- ElevenLabs exports **mono**. Remotion plays mono on both channels of the stereo render,
  which sounds ~3 LU louder than the file reads — `footage.mjs clip --match` accounts for it.
- Keep the VO untouched (no re-encode). Cut silences in the EDIT PLAN, not in the file.
- Never re-time the narration to fit visuals; visuals follow the voice.

## 3. Footage: find, check, fetch, find the moment, cut

```bash
node <skill>/scripts/footage.mjs search "como funciona um painel solar" --cc --n 8
node <skill>/scripts/footage.mjs fetch <id-or-url>            # CC only by default
node <skill>/scripts/footage.mjs import aula.mp4 --title "Aula" --channel "Meu canal" --license "Own footage" --subs aula.vtt
node <skill>/scripts/footage.mjs moments <id> "silício,elétrons,corrente"
node <skill>/scripts/footage.mjs clip <id> 3.6 10.8 --name celula --match public/voice/vo.mp3
node <skill>/scripts/footage.mjs credits
```

- `fetch` saves `source.mp4` (H.264 ≤ 1080p), `manifest.json` (title, channel, url, license,
  rights) and `transcript.json` from the video's subtitles (manual preferred over automatic;
  word timings from YouTube's json3 when available).
- `moments` searches the transcript for keywords (accent-insensitive) and proposes clip
  windows aligned to phrase edges — use it to find where the source *says* the thing.
  For pure visuals (no speech needed), look at stills: `review-frames.mjs` on a composition
  that plays the source, or scrub it in Remotion Studio.
- `clip` makes a frame-exact, re-encoded copy with audio normalized to the VO's speech
  loudness (`--match`) and a `.transcript.json` in clip time (captions line up).
- yt-dlp is found at `$YTDLP`, `./.tools/yt-dlp` or on PATH; it uses Remotion's bundled
  ffmpeg and Node as its JS runtime — no other installs.

## 4. The EDIT PLAN (`edit.json`)

The agent writes the plan; `EditTimeline` renders it. Segments play in order; the output
duration is the sum of segment durations.

```json
{
  "voice": { "src": "voice/vo.mp3", "map": "voice/vo.voice.json" },
  "captions": { "style": "pill", "y": 0.62, "maxWords": 3, "on": "footage" },
  "transition": "cut",
  "drift": 0.04,
  "segments": [
    { "kind": "vo", "from": 0, "to": 2.75, "visual": { "type": "number", "value": 8, "suffix": " min", "label": "do Sol até a Terra" } },
    { "kind": "vo", "from": 2.75, "to": 4.78, "visual": { "type": "broll", "src": "broll/<id>/source.mp4", "from": 0.4, "fit": "cover", "focus": [82, 40], "credit": "Canal · YouTube (CC BY)" } },
    { "kind": "vo", "from": 8.47, "to": 12.01, "visual": { "type": "kinetic", "emphasis": ["silício"] } },
    { "kind": "bite", "src": "broll/<id>/clips/celula.mp4", "from": 0, "to": 7.2, "fit": "contain-blur", "credit": "Canal · YouTube (CC BY)", "transcript": "broll/<id>/clips/celula.transcript.json" },
    { "kind": "vo", "from": 15.28, "to": 20.77, "visual": { "type": "title", "kicker": "Ou seja", "text": "…", "emphasis": ["casa"] } }
  ]
}
```

Visual types: `title`, `kinetic` (words appear when spoken), `number` (CountUp), `broll`
(muted footage; `cover` + `focus`, or `contain-blur` for horizontal sources in vertical),
`image`, `scene` (your own component, passed in `scenes`). A `bite` pauses the narration and
plays the clip WITH its audio, captioned from its transcript. Optional `music` ducks under bites.

Composition wiring (see `showcase/.../VoiceEdit.tsx`):

```tsx
calculateMetadata: async ({ props }) => {
  const raw = await (await fetch(staticFile(props.planPath))).json();
  const { plan, voice } = await resolveEditAssets(raw);
  return { durationInFrames: Math.ceil(planTimeline(plan).duration * fps), props: { ...props, plan, voice } };
}
// component: <EditTimeline plan={plan} voice={voice} scenes={{ hook: MyHook }} />
```

## 5. Editing rules for VO-driven videos

- **Cut on the voice.** Scene changes on phrase boundaries (pauses in `voice.json`); visual
  swaps inside a phrase only on word boundaries. Never mid-word.
- **Change the picture every 2–3 s** in reels (`rhythm-audit` flags dead stretches). A long
  phrase = two visuals (e.g. number → B-roll).
- **Match visual to words**: the B-roll shows what the narrator says *at that moment*; the
  kinetic word lands on its spoken time; emphasis on the 1–2 words that carry the meaning.
- **Sound bites earn their place**: use one when the source says it better (an expert, a
  real sound, a reaction). Introduce it in the VO ("escuta como ele explica"), keep it
  ≤ 10 s, cut out on a pause, return to the VO.
- **Footage fit**: horizontal source in vertical video → `contain-blur` for content with
  text/faces at the edges, `cover` + `focus` when the subject is clearly placed. Slow push
  on all footage (the default `push`) so stock never looks frozen.
- **Captions** over footage (`on: "footage"`) — type scenes already show the words.
  Keep them inside the safe zone (y ≈ 0.58–0.65 on 9:16).
- **Loudness**: VO and bites at the same speech loudness (`clip --match`); music −18 to −20
  dB under voice and lower during bites (`duckedVolume`); final mix ≈ −14 LUFS.
- **First frame** of every scene already in motion (no empty frame between cuts).

## 6. QA for this mode

- [ ] Every clip: license recorded, credit on screen, listed by `footage.mjs credits`
- [ ] No clip from a non-CC source without a written `--rights` reason from the user
- [ ] Sound bites: real words of the source, ≤ ~10 s, captioned, level matched (measure LUFS)
- [ ] Visual changes on word/phrase boundaries; nothing mid-word
- [ ] `rhythm-audit` on the RENDER (its own audio): no dead stretch except reading holds
      (`--audio` only when the external audio is aligned with the video — not with inserted bites)
- [ ] Storyboard sheet reviewed; captions never cover faces or the source's own text
