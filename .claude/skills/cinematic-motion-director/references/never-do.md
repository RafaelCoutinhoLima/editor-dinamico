# Never do: negative rules learned from shipped edits

Every line here broke a real delivery (Oct–Nov 2026: tech reels, a mayor's-award film, faith and
health creators' talking heads, a fintech promo, a food-delivery explainer). Read this before the
storyboard and again before the final render. Each rule says what went wrong and the check.

## Spacing and layout

- **Never let two elements overlap**: text on text, text on the caption band, a credit on the
  brand chip, a growing box on its own label, a list of chips running into a grid. *Happened:
  six overlaps after one panel got 80 px shorter, all invisible on a 1-still-per-second sheet.*
  Check: 3 frames per shot (start + 0.3 s, middle, end) at ≥ 360 px, after **every** layout or
  timing change; animated elements at their largest frame.
- **Never trust a storyboard sheet for spacing.** It samples between the collisions.
- **Never place by independent absolute positions in a stack** (kicker → headline → sub →
  chips): flow layout with explicit margins; size grids for their **final** count.
- **Never let a long word run past the 60 px side margin**: size from the box, not the text
  (`investimentos`, `Prefeitura`).
- **Never put text in the top ~220 px or the bottom ~320 px** of a 9:16 frame (platform UI);
  captions sit in one fixed band with a clear gap above.
- **Never stack punch-ins** past ~3–3.5 % total: edge content leaves the side margins.
- **Never put a graphic over the face** — behind the head (person matte) or beside it
  (`placeBeside`); full-type moments slide the camera down so the type sits above the face.
- **Never crop the speaker's head** in split screen or zooms; scale the camera (e.g. 0.72) and
  fill the sides with a blurred copy instead of cropping a close-framed face.
- **Never crop illustrated characters or logos** (hands, feet, edges): `objectFit: contain`.
- **Never position from the wrong clock**: inside a shot use shot-local time; convert voice cues
  with one helper (`useAt(shotStart)`). Mixing absolute and local time put flow packets off
  their lines.

## Color, type and brand

- **Never use a second accent color** for a creator with one (Fabio: Claude orange only — green
  and red highlights read as "not my identity").
- **Never switch a light-theme brand to a dark "terminal" look** because the topic is tech.
- **Never add a second font family** (mono for typewriter text, kickers) when the identity is
  one family; vary weight and size instead.
- **Never drop a logo on a background without checking it in the final frame**: site-header
  logos and coats of arms are often **white** and vanish on light paper — recolor to ink
  (`filter: brightness(0)`) or put it on a dark tile.
- **Never guess brand hex values**: sample them from official images.
- **Never put a comment inside a TS object before a key on the same line**
  (`red: "#…", // note line: …` swallowed `line:` and broke the build).

## Audio

- **Never cut breaths by Whisper word gaps**: its timestamps once deleted a word. Cut by
  energy, then re-transcribe and fail on any missing word (`cut-breaths.py --verify`); check
  hard spots by ear-proxy (e.g. "Lá em Salmo 139").
- **Never speed up before cutting breaths**, and never forget the user's speed (1.04–1.10×).
- **Never use whooshes, drags or synthesized typewriter clacks + bells** for creators who
  asked for calm: soft low mouse clicks on cuts (~20 dB under the voice), real soft keyboard
  (~25 dB under), earshot bank or real CC0 recordings.
- **Never add background music when the user adds it in-app or didn't ask**; when a track is
  given, mix it ~17 dB under speech (~13 dB in gaps) with ducking.
- **Never keep an AI avatar's own audio**: drop it and re-time its frames to the real voice.
- **Never place an SFX by its file start**: align on its measured onset / peak.

## Story, images and endings

- **Never ship a news or company story as pure motion graphics**: real photos of the people,
  logos and places named (press/Wikimedia/CC0, credit in one fixed spot).
- **Never hold one shot longer than ~2.5–3 s** in a creator reel (new shot every 1.5–2.5 s).
- **Never add a @handle / signature end card to client or friend videos** unless asked (his
  own reels do get the follow card).
- **Never open on black or an empty frame** unless asked: the hook is on screen in 0.5 s.
- **Never invent numbers, features, UI or testimonials**; never show a number you did not check.

## Rendering and delivery

- **Never render with every client's assets in `public/`**: each bundle copies all of it; use
  `--public-dir=pub_<client>` and delete `remotion-webpack-bundle-*` / `remotion-*-assets*`
  from the temp folder after renders (the disk filled up).
- **Never pass `--concurrency` above the core count** (a 1-core machine errors out).
- **Never deliver without opening the final MP4** (not the preview, not the sheet) — and say
  what was checked; never claim a render or a check that did not happen.
- **Never redo the whole video after feedback**: fix only the named stretch, re-render, stop.
