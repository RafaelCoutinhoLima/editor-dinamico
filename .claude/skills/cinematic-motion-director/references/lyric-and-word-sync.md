# Lyric Videos & Word-Level Sync

Every word lands on the frame it is sung or spoken. The same pipeline powers lyric videos,
karaoke captions and kinetic narration.

## 1. Rights first

The engine can be MIT; the **song, the lyrics and the timing data are the authors'**. Make a
lyric video only for music the user owns or has written permission to use, and say so in the
brief. Never reuse lyrics, timings or audio from someone else's repository.

## 2. Word timings

1. Get the clean vocal if possible (stem), otherwise the full mix.
2. Transcribe with word timestamps (`scripts/voice-map.mjs`, or faster-whisper
   `word_timestamps=True` with `initial_prompt` = the real lyrics, so spelling matches).
3. **Align to the real lyrics**, not to the transcript: map each lyric word to the nearest
   transcribed word (fuzzy match) and keep the timestamp; fill misses by interpolating
   between neighbours.
4. Show the user **10 lines** with their start times before building, and fix any line that
   is off by more than 2 frames (at 60 fps: 33 ms).
5. Store as `src/lyrics.json`: `[{line, words:[{w, s, e}]}]`.

Speech (narration) uses the same JSON; music cues stay on the beat grid
(`beat-map.mjs`) while words follow the voice.

## 3. Scene plan

- 6–10 scenes, one per song section (verse/chorus/bridge); one visual idea per scene and one
  transition idea per section change. Approve the plan before building.
- Chorus = same visual system each time, escalated (bigger, more layers), so it reads as a
  chorus.
- Word treatment by stress: stressed syllables get scale/weight/color, unstressed stay small.
  Never animate every word the same way.
- Keep each line on screen ≥ its sung duration + 0.25 s; dense rap lines → show 2–3 words at a
  time.

## 4. Rendering

- 1920x1080 or 1080x1920 at **60 fps** for lyric work (word hits look late at 30 fps).
- Long songs at 4K are heavy (tens of minutes and >20 GB RAM): render a 30 s chorus first,
  review, then the full song in chunks and concatenate.

## 5. Checks

- Every word starts within ±2 frames of its timestamp (spot-check 10 words across the song).
- No line overlaps the next; nothing crosses the safe zone.
- The music is cleared (owner or written permission) — written in the delivery message.
