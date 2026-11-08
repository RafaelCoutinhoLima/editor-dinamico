#!/usr/bin/env node
/**
 * Music first: measure the track, then animate to it.
 * Finds BPM, beat times, downbeats (4/4), the drop and section changes, and writes JSON
 * you feed to the kit (`beatPulse`, `snapToBeat`, `cues`). Run from the Remotion project root:
 *
 *   node <skill>/scripts/beat-map.mjs public/music.mp3
 *   node <skill>/scripts/beat-map.mjs public/music.mp3 --out src/beats.json --bpm 124
 *
 * --bpm forces the tempo when you know it (detection can pick half/double time on sparse tracks).
 * Heuristic DSP, no dependencies: verify by ear in Studio — a click on every downbeat helps.
 */
import fs from "node:fs";
import { parseArgs } from "node:util";
import { decodeMono } from "./lib/media.mjs";

const { values: a, positionals } = parseArgs({
  allowPositionals: true,
  options: { out: { type: "string" }, bpm: { type: "string" }, min: { type: "string", default: "70" }, max: { type: "string", default: "180" } },
});
const file = positionals[0];
if (!file) {
  console.error("Usage: beat-map.mjs <audio> [--out beats.json] [--bpm 120]");
  process.exit(1);
}

const SR = 11025;
const HOP = 128; // ~11.6 ms per envelope step
const samples = await decodeMono(file, SR);
const hopSec = HOP / SR;
const n = Math.floor(samples.length / HOP);

// Two envelopes: full band (onsets) and a crude low band (kick → downbeats, energy → drop).
const full = new Float64Array(n);
const low = new Float64Array(n);
let lp = 0;
for (let i = 0; i < n; i++) {
  let ef = 0;
  let el = 0;
  for (let k = i * HOP; k < (i + 1) * HOP; k++) {
    const s = samples[k];
    lp += 0.06 * (s - lp); // one-pole low-pass ≈ 110 Hz
    ef += s * s;
    el += lp * lp;
  }
  full[i] = Math.log1p(1000 * Math.sqrt(ef / HOP));
  low[i] = Math.sqrt(el / HOP);
}
const onset = new Float64Array(n);
onset[0] = full[0]; // treat the time before the file as silence, so a hit on 0.0 s counts
for (let i = 1; i < n; i++) onset[i] = Math.max(0, full[i] - full[i - 1]);

// Tempo: autocorrelation of the onset envelope, weighted toward ~120 BPM.
const toLag = (bpm) => 60 / bpm / hopSec;
let period;
if (a.bpm) {
  period = toLag(Number(a.bpm));
} else {
  let best = -1;
  for (let bpm = Number(a.min); bpm <= Number(a.max); bpm += 0.25) {
    const lag = toLag(bpm);
    let s = 0;
    for (let i = 0; i + lag + 1 < n; i++) {
      const j = i + lag;
      const f = j - Math.floor(j);
      s += onset[i] * (onset[Math.floor(j)] * (1 - f) + onset[Math.floor(j) + 1] * f);
    }
    const w = Math.exp(-0.5 * (Math.log2(bpm / 120) / 0.9) ** 2);
    if (s * w > best) (best = s * w), (period = lag);
  }
}

// Grid fit: for a period, the phase that lands on the most onset energy.
const gridFit = (per) => {
  let best = { score: -1, phase: 0 };
  for (let p = 0; p < per; p += 0.5) {
    let s = 0;
    for (let t = p; t < n; t += per) s += onset[Math.round(t)] ?? 0;
    if (s > best.score) best = { score: s, phase: p };
  }
  return best;
};
// Fine tempo search (±3 %, 0.02 BPM steps) so the grid doesn't drift over long tracks.
if (!a.bpm) {
  const coarse = 60 / (period * hopSec);
  let best = -1;
  for (let b = coarse * 0.97; b <= coarse * 1.03; b += 0.02) {
    const f = gridFit(toLag(b));
    if (f.score > best) (best = f.score), (period = toLag(b));
  }
}
const bpm = 60 / (period * hopSec);
const { phase } = gridFit(period);

// Beats on the grid, nudged to the strongest onset within ±8 % of a period.
const beats = [];
for (let t = phase; t < n; t += period) {
  const r = Math.round(period * 0.08);
  let bi = Math.round(t);
  for (let k = Math.max(0, bi - r); k <= Math.min(n - 1, Math.round(t) + r); k++) if (onset[k] > onset[bi]) bi = k;
  beats.push(Number((bi * hopSec).toFixed(3)));
}

// Downbeats: which of the 4 beat positions carries the most low-end.
const lowAt = (sec) => {
  const i = Math.round(sec / hopSec);
  let s = 0;
  for (let k = i; k < Math.min(n, i + 6); k++) s += low[k];
  return s;
};
const slot = [0, 1, 2, 3].map((o) => beats.filter((_, i) => i % 4 === o).reduce((s, b) => s + lowAt(b), 0));
const first = slot.indexOf(Math.max(...slot));
const downbeats = beats.filter((_, i) => i % 4 === first);

// Energy per bar → drop (biggest jump between the 2 bars before and the 2 bars after) + section changes.
const barEnergy = downbeats.map((d, i) => {
  const end = downbeats[i + 1] ?? d + (4 * 60) / bpm;
  let s = 0;
  let c = 0;
  for (let k = Math.round(d / hopSec); k < Math.min(n, Math.round(end / hopSec)); k++) (s += full[k]), c++;
  return c ? s / c : 0;
});
const jumps = barEnergy.map((_, i) => {
  if (i < 2 || i > barEnergy.length - 2) return { t: downbeats[i], jump: 0 };
  const before = (barEnergy[i - 1] + barEnergy[i - 2]) / 2;
  const after = (barEnergy[i] + (barEnergy[i + 1] ?? barEnergy[i])) / 2;
  return { t: downbeats[i], jump: after - before };
});
const sorted = [...jumps].sort((x, y) => Math.abs(y.jump) - Math.abs(x.jump));
const drop = [...jumps].sort((x, y) => y.jump - x.jump)[0];
// Non-maximum suppression: keep the strongest change within any 4-bar window.
const bar = (4 * 60) / bpm;
const sections = [];
for (const j of sorted) {
  if (Math.abs(j.jump) <= 0.15 || sections.length >= 6) continue;
  if (sections.every((t) => Math.abs(t - j.t) > bar * 3.5)) sections.push(j.t);
}
sections.sort((x, y) => x - y);

const result = {
  file,
  duration: Number((samples.length / SR).toFixed(2)),
  bpm: Number(bpm.toFixed(2)),
  beats,
  downbeats,
  drop: drop && drop.jump > 0.15 ? drop.t : null,
  sections,
};

if (a.out) fs.writeFileSync(a.out, JSON.stringify(result, null, 2));
console.log(`${file} · ${result.duration} s · ${result.bpm} BPM · ${beats.length} beats · ${downbeats.length} bars`);
console.log(`first downbeat ${downbeats[0]} s · drop ${result.drop ?? "none found"} · section changes ${sections.join(", ") || "none"}`);
console.log(`bar length ${((4 * 60) / bpm).toFixed(3)} s → good cut points: downbeats; hits: beats; big reveal: drop`);
if (a.out) console.log(`→ ${a.out}`);
