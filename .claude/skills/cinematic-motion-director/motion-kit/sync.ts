/**
 * Voice/music sync. Write cue points in SECONDS (from the real audio file,
 * captions JSON or a transcript with timestamps) and convert once:
 *
 *   const cue = cues(fps, { hook: 0, problem: 2.35, reveal: 5.1, cta: 11.8 });
 *   <Sequence from={cue.reveal}>...</Sequence>
 *
 * Never guess timings by eye when an audio file exists — measure it.
 */
export const cues = <K extends string>(fps: number, seconds: Record<K, number>): Record<K, number> =>
  Object.fromEntries(Object.entries(seconds).map(([k, s]) => [k, Math.round((s as number) * fps)])) as Record<K, number>;

/** Frames between two cues — the duration of the scene that starts at `from`. */
export const span = <K extends string>(c: Record<K, number>, from: K, to: K): number => Math.max(1, c[to] - c[from]);

/**
 * Speech-rate estimate for scripts without audio yet.
 * PT-BR / EN conversational narration ≈ 2.5–3 words per second; ads read faster (~3.2).
 */
export const estimateSpeechSeconds = (script: string, wordsPerSecond = 2.7): number =>
  Math.round((script.split(/\s+/).filter(Boolean).length / wordsPerSecond) * 10) / 10;

/**
 * Beat helpers — feed them `beats`/`downbeats` (seconds) from scripts/beat-map.mjs.
 *
 *   const pulse = beatPulse(frame, fps, beats.downbeats);      // 1 on the hit → 0
 *   <div style={{ scale: String(1 + 0.04 * pulse) }} />
 *   <Sequence from={snapToBeat(2.1, beats.downbeats, fps)}>  // cut on the nearest downbeat
 */
export const beatPulse = (frame: number, fps: number, beatsSec: readonly number[], decaySec = 0.25): number => {
  const t = frame / fps;
  let last = -Infinity;
  for (const b of beatsSec) {
    if (b > t) break;
    last = b;
  }
  const dt = t - last;
  return dt < 0 || !Number.isFinite(dt) ? 0 : Math.exp(-dt / (decaySec / 3));
};

/** Index of the last beat at or before `frame` (-1 before the first). Use for per-beat switches. */
export const beatIndex = (frame: number, fps: number, beatsSec: readonly number[]): number => {
  const t = frame / fps;
  let i = -1;
  while (i + 1 < beatsSec.length && beatsSec[i + 1] <= t) i++;
  return i;
};

/** Frame of the beat nearest to `seconds`. Snap cuts and hero hits to the music. */
export const snapToBeat = (seconds: number, beatsSec: readonly number[], fps: number): number => {
  let best = beatsSec[0] ?? seconds;
  for (const b of beatsSec) if (Math.abs(b - seconds) < Math.abs(best - seconds)) best = b;
  return Math.round(best * fps);
};
