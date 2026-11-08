#!/usr/bin/env node
/**
 * Voice map: turn a finished voiceover (ElevenLabs or any VO) into word + phrase timings that
 * drive the whole edit. Run from the Remotion project root.
 *
 *   # ElevenLabs TTS "with-timestamps" response (alignment / normalized_alignment):
 *   node <skill>/scripts/voice-map.mjs public/voice/vo.mp3 --alignment public/voice/vo.alignment.json
 *   # ElevenLabs Speech-to-Text, OpenAI verbose_json, Remotion Caption[] or whisper.cpp output:
 *   node <skill>/scripts/voice-map.mjs public/voice/vo.mp3 --transcript public/voice/vo.stt.json
 *   # Only the audio + the script text (no timestamps): aligned on the pauses of the audio
 *   node <skill>/scripts/voice-map.mjs public/voice/vo.mp3 --script roteiro.txt
 *   # Only the audio: local Whisper via @remotion/install-whisper-cpp (downloads a model once)
 *   node <skill>/scripts/voice-map.mjs public/voice/vo.mp3 --whisper --lang pt --model small
 *
 * Output (default <audio>.voice.json): { audio, duration, words[{text,start,end}],
 * phrases[{text,start,end,firstWord,lastWord}], pauses[{start,end}] } — seconds.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { parseArgs } from "node:util";
import { probeAudio, remotionTool, silences } from "./lib/media.mjs";

const { values: a, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    alignment: { type: "string" },
    transcript: { type: "string" },
    script: { type: "string" },
    whisper: { type: "boolean", default: false },
    lang: { type: "string", default: "pt" },
    model: { type: "string", default: "small" },
    out: { type: "string" },
    pause: { type: "string", default: "0.28" }, // min silence (s) that counts as a phrase break
  },
});
const audio = positionals[0];
if (!audio || !fs.existsSync(audio)) {
  console.error("Usage: voice-map.mjs <voice.mp3> [--alignment f.json | --transcript f.json | --script f.txt | --whisper]");
  process.exit(1);
}
const ROOT = process.cwd();

// ---------- words from the different sources ----------
const fromCharAlignment = (al) => {
  const words = [];
  let cur = null;
  al.characters.forEach((ch, i) => {
    const s = al.character_start_times_seconds[i];
    const e = al.character_end_times_seconds[i];
    if (/\s/.test(ch)) {
      if (cur) words.push(cur), (cur = null);
      return;
    }
    if (!cur) cur = { text: "", start: s, end: e };
    cur.text += ch;
    cur.end = e;
  });
  if (cur) words.push(cur);
  return words;
};

const fromTranscript = (j) => {
  if (Array.isArray(j) && j[0] && "startMs" in j[0]) // Remotion Caption[] (whisper.cpp toCaptions, @remotion/* converters)
    return j.map((c) => ({ text: c.text.trim(), start: c.startMs / 1000, end: c.endMs / 1000 })).filter((w) => w.text);
  if (j.alignment || j.normalized_alignment || j.characters) return fromCharAlignment(j.alignment || j.normalized_alignment || j);
  if (Array.isArray(j.words) && j.words[0] && "type" in j.words[0]) // ElevenLabs Speech-to-Text
    return j.words.filter((w) => w.type === "word").map((w) => ({ text: w.text, start: w.start, end: w.end }));
  if (Array.isArray(j.segments) && j.segments[0]?.words?.[0]?.start_time !== undefined) // ElevenLabs segmented
    return j.segments.flatMap((s) => s.words.map((w) => ({ text: w.text, start: w.start_time, end: w.end_time })));
  if (Array.isArray(j.words) && j.words[0] && "word" in j.words[0]) // OpenAI verbose_json
    return j.words.map((w) => ({ text: w.word.trim(), start: w.start, end: w.end }));
  throw new Error("Unknown transcript format. Supported: ElevenLabs alignment / STT / segmented, OpenAI verbose_json, Remotion Caption[].");
};

// Script + audio only: speech chunks between pauses, phrases distributed by character count.
const fromScript = async (text, duration) => {
  const pauses = await silences(audio, -38, Number(a.pause));
  const speech = [];
  let t = 0;
  for (const p of pauses) {
    if (p.start - t > 0.05) speech.push({ start: t, end: p.start });
    t = p.end;
  }
  if (duration - t > 0.05) speech.push({ start: t, end: duration });
  const phrases = text.replace(/\s+/g, " ").trim().split(/(?<=[.!?…:;])\s+/).filter(Boolean);
  // Work in "speech time" (pauses removed). Phrase boundaries are predicted by character share,
  // then snapped to the nearest real pause (monotonic); with no pause nearby, split inside speech.
  const total = speech.reduce((s, c) => s + (c.end - c.start), 0);
  const gaps = []; // speech-time position of each pause between chunks
  let acc = 0;
  speech.forEach((c, i) => {
    acc += c.end - c.start;
    if (i < speech.length - 1) gaps.push({ at: acc, endReal: c.end, startReal: speech[i + 1].start });
  });
  const toReal = (T) => {
    let rest = T;
    for (const c of speech) {
      if (rest <= c.end - c.start) return c.start + rest;
      rest -= c.end - c.start;
    }
    return speech[speech.length - 1].end;
  };
  const chars = phrases.map((p) => p.length);
  const allChars = chars.reduce((x, y) => x + y, 0);
  const bounds = [{ end: speech[0].start }]; // bounds[k] = where phrase k starts (real) + where k-1 ended
  let used = -1;
  let cum = 0;
  for (let k = 0; k < phrases.length - 1; k++) {
    cum += chars[k];
    const T = (total * cum) / allChars;
    const phraseLen = (total * chars[k]) / allChars;
    const tol = Math.max(0.35, phraseLen * 0.3);
    let best = -1;
    for (let j = used + 1; j < gaps.length; j++) {
      if (gaps[j].at > T + tol) break;
      if (Math.abs(gaps[j].at - T) <= tol && (best < 0 || Math.abs(gaps[j].at - T) < Math.abs(gaps[best].at - T))) best = j;
    }
    if (best >= 0) {
      used = best;
      bounds.push({ prevEnd: gaps[best].endReal, start: gaps[best].startReal });
    } else {
      const r = toReal(T);
      bounds.push({ prevEnd: r, start: r });
    }
  }
  const words = [];
  phrases.forEach((ph, k) => {
    const s = k === 0 ? speech[0].start : bounds[k].start;
    const e = k === phrases.length - 1 ? speech[speech.length - 1].end : bounds[k + 1].prevEnd;
    const ws = ph.split(" ");
    const n = ws.reduce((x, w) => x + w.length + 1, 0);
    let pos = 0;
    for (const w of ws) {
      const w0 = s + ((e - s) * pos) / n;
      pos += w.length + 1;
      words.push({ text: w, start: w0, end: s + ((e - s) * pos) / n });
    }
  });
  return words;
};

const fromWhisper = async () => {
  const req = createRequire(path.join(ROOT, "package.json"));
  let w;
  try {
    w = req("@remotion/install-whisper-cpp");
  } catch {
    throw new Error("Install it first: npx remotion add @remotion/install-whisper-cpp");
  }
  const whisperPath = path.join(ROOT, ".tools", "whisper.cpp");
  await w.installWhisperCpp({ to: whisperPath, version: "1.6.0" }); // the version the official TikTok template uses
  await w.downloadWhisperModel({ model: a.model, folder: whisperPath });
  const wav = path.join(ROOT, ".tools", "voice-16k.wav");
  await remotionTool("ffmpeg", ["-y", "-loglevel", "error", "-i", audio, "-ar", "16000", "-ac", "1", wav]);
  const out = await w.transcribe({ inputPath: wav, whisperPath, whisperCppVersion: "1.6.0", model: a.model, language: a.lang, tokenLevelTimestamps: true });
  return fromTranscript(w.toCaptions({ whisperCppOutput: out }).captions);
};

// ---------- main ----------
const { duration } = await probeAudio(audio);
let words;
let source;
if (a.alignment) (words = fromTranscript(JSON.parse(fs.readFileSync(a.alignment, "utf8")))), (source = "elevenlabs-alignment");
else if (a.transcript) (words = fromTranscript(JSON.parse(fs.readFileSync(a.transcript, "utf8")))), (source = "transcript");
else if (a.script) (words = await fromScript(fs.readFileSync(a.script, "utf8"), duration)), (source = "script+pauses");
else if (a.whisper) (words = await fromWhisper()), (source = `whisper-${a.model}`);
else throw new Error("Give one of --alignment, --transcript, --script or --whisper.");

words = words.map((w) => ({ text: w.text, start: +w.start.toFixed(3), end: +Math.max(w.end, w.start + 0.04).toFixed(3) }));

// Phrases: sentence punctuation, a real pause, or 14 words.
const phrases = [];
let first = 0;
words.forEach((w, i) => {
  const gap = words[i + 1] ? words[i + 1].start - w.end : Infinity;
  if (/[.!?…:;]$/.test(w.text) || gap >= Number(a.pause) || i - first >= 13 || i === words.length - 1) {
    phrases.push({ text: words.slice(first, i + 1).map((x) => x.text).join(" "), start: words[first].start, end: w.end, firstWord: first, lastWord: i });
    first = i + 1;
  }
});
const pauses = phrases.slice(1).map((p, i) => ({ start: phrases[i].end, end: p.start })).filter((p) => p.end - p.start > 0.05);

const out = a.out || audio.replace(/\.[^.]+$/, "") + ".voice.json";
const rel = (p) => path.relative(path.join(ROOT, "public"), path.resolve(p)).split(path.sep).join("/");
fs.writeFileSync(out, JSON.stringify({ audio: rel(audio), source, duration: +duration.toFixed(3), words, phrases, pauses }, null, 2));
console.log(`${audio} · ${duration.toFixed(2)} s · ${words.length} words · ${phrases.length} phrases · source: ${source}`);
phrases.slice(0, 40).forEach((p, i) => console.log(`  ${String(i + 1).padStart(2)}  ${p.start.toFixed(2).padStart(6)}–${p.end.toFixed(2).padEnd(6)}  ${p.text}`));
console.log(`→ ${out}`);
