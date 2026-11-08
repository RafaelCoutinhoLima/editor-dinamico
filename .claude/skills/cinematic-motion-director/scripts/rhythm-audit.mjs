#!/usr/bin/env node
/**
 * Rhythm critic: measures a RENDERED video instead of trusting the code.
 * Finds dead stretches (nothing moves), single-frame pops, cuts, shot lengths, the motion-energy curve,
 * whether there are real holds, and — when there is audio — whether cuts land on pauses.
 * Run from the Remotion project root (uses `npx remotion ffmpeg`, no extra installs):
 *
 *   node <skill>/scripts/rhythm-audit.mjs out/video.mp4
 *   node <skill>/scripts/rhythm-audit.mjs out/video.mp4 --audio public/voiceover.mp3
 *   node <skill>/scripts/rhythm-audit.mjs out/video.mp4 --dead 1.2 --json
 *   node <skill>/scripts/rhythm-audit.mjs out/loop.mp4 --loop        # also checks the loop seam
 *   node <skill>/scripts/rhythm-audit.mjs out/promo.mp4 --beats src/beats.json   # cuts vs the music grid
 *
 * Thresholds are heuristics: read the flags, then look at those moments before changing anything.
 */
import fs from "node:fs";
import { parseArgs } from "node:util";
import { probe, rawFrames, silences } from "./lib/media.mjs";

const { values: a, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    audio: { type: "string" },
    dead: { type: "string", default: "2" }, // seconds without visible change = dead stretch
    json: { type: "boolean", default: false },
    loop: { type: "boolean", default: false },
    beats: { type: "string" }, // beats.json from beat-map.mjs
  },
});
const file = positionals[0];
if (!file) {
  console.error("Usage: rhythm-audit.mjs <video.mp4> [--audio voice.mp3] [--dead 1.5] [--json]");
  process.exit(1);
}

const STILL = 0.001; // mean abs luma diff per frame below which nothing visibly moves
const LOW = 0.006; // "hold" territory: slow drift, grain, a counter ticking
const CUT = 0.04; // share of pixels changing a lot at once = cut (robust on dark frames)

const info = await probe(file);
const w = 96;
const h = Math.max(2, Math.round((w * info.height) / info.width / 2) * 2);
const frames = await rawFrames(file, w, h, "gray");
const fps = info.fps;

// diff = mean luma change (motion amount); changed = share of pixels that jumped (cut detector).
const diff = [0];
const changed = [0];
for (let i = 1; i < frames.length; i++) {
  const f = frames[i];
  const p = frames[i - 1];
  let s = 0;
  let c = 0;
  for (let k = 0; k < f.length; k++) {
    const d = Math.abs(f[k] - p[k]);
    s += d;
    if (d > 24) c++;
  }
  diff.push(s / f.length / 255);
  changed.push(c / f.length);
}

// Cuts: spikes well above the local level.
const cuts = [];
for (let i = 1; i < diff.length; i++) {
  const win = changed.slice(Math.max(1, i - 8), i).concat(changed.slice(i + 1, i + 9)).sort((x, y) => x - y);
  const median = win[Math.floor(win.length / 2)] ?? 0;
  if (changed[i] > CUT && changed[i] > Math.max(median * 4, 0.02) && (cuts.length === 0 || i - cuts[cuts.length - 1] > fps * 0.25)) cuts.push(i);
}

// Pops: a single frame that differs from BOTH neighbours while the neighbours match each other
// (flash, missing asset, wrong state for one frame). Cuts don't return, pops do.
const pops = [];
for (let i = 1; i + 1 < frames.length; i++) {
  if (diff[i] < 0.01) continue;
  let back = 0;
  for (let k = 0; k < frames[i].length; k++) back += Math.abs(frames[i + 1][k] - frames[i - 1][k]);
  back = back / frames[i].length / 255;
  if (back < diff[i] * 0.3 && diff[i + 1] > diff[i] * 0.5) pops.push(i);
}

// Dead stretches: runs of frames with no visible change.
const dead = [];
let runStart = null;
for (let i = 1; i <= diff.length; i++) {
  const still = i < diff.length && diff[i] < STILL;
  if (still && runStart === null) runStart = i;
  if (!still && runStart !== null) {
    if ((i - runStart) / fps >= Number(a.dead)) dead.push({ start: runStart / fps, end: i / fps, endHold: i >= diff.length - 1 });
    runStart = null;
  }
}

// Energy per second.
const seconds = Math.ceil(frames.length / fps);
const energy = Array.from({ length: seconds }, (_, s) => {
  const seg = diff.slice(Math.round(s * fps), Math.round((s + 1) * fps));
  return seg.reduce((x, y) => x + y, 0) / Math.max(1, seg.length);
});
const maxE = Math.max(...energy, 1e-9);
const bars = "▁▂▃▄▅▆▇█";
const curve = energy.map((e) => bars[Math.min(7, Math.floor((e / maxE) * 7.99))]).join("");
const holdFrames = diff.filter((d, i) => i > 0 && d < LOW).length;

const shots = [0, ...cuts, frames.length].slice(1).map((c, i, arr) => (c - (i === 0 ? 0 : arr[i - 1])) / fps);
const sortedShots = [...shots].sort((x, y) => x - y);

let pauses = null;
let alignedCuts = null;
if (a.audio || info.hasAudio) {
  pauses = await silences(a.audio ?? file);
  const near = (t) => pauses.some((p) => Math.abs(p.start - t) < 0.15 || Math.abs(p.end - t) < 0.15);
  alignedCuts = cuts.filter((c) => near(c / fps)).length;
}

// Loop seam: last → first frame should look like any ordinary frame step, not a jump.
let seam = null;
if (a.loop) {
  const f = frames[frames.length - 1];
  let s = 0;
  for (let k = 0; k < f.length; k++) s += Math.abs(frames[0][k] - f[k]);
  // Compare with the steps right around the seam: a seam placed mid-morph is SUPPOSED to move.
  const typical = Math.max(diff[1] ?? 0, diff[diff.length - 1] ?? 0, 0.001);
  seam = { diff: Number((s / f.length / 255).toFixed(4)), typical: Number(typical.toFixed(4)) };
}

const flags = [];
if (seam && seam.diff > Math.max(seam.typical * 2, 0.004)) flags.push(`Loop seam jumps (${seam.diff} vs ${seam.typical} for the neighbouring steps): last frame must lead into frame 0 — match geometry, content, camera and cursor.`);
pops.forEach((f) => flags.push(`Single-frame pop at frame ${f} (${(f / fps).toFixed(2)} s): one frame differs from both neighbours — check for a flash, a late asset or a state glitch.`));
dead.filter((d) => !d.endHold).forEach((d) => flags.push(`Dead stretch ${d.start.toFixed(2)}–${d.end.toFixed(2)} s: nothing moves. If it is a reading hold, keep it but add drift (slow push, parallax, grain); otherwise cut it.`));
dead.filter((d) => d.endHold).forEach((d) => flags.push(`Final ${(d.end - d.start).toFixed(1)} s are a static hold — fine for a CTA/end card, otherwise trim.`));
if (holdFrames / frames.length < 0.12) flags.push("Almost no calm frames: everything is moving all the time. Add readable holds.");
if (sortedShots.length && sortedShots[sortedShots.length - 1] > 6) flags.push(`Longest shot is ${sortedShots[sortedShots.length - 1].toFixed(1)} s — check it keeps evolving (for ads, aim for a change every 1.5–3 s).`);
if (energy.length > 2 && energy[0] < maxE * 0.25) flags.push("First second is low-energy: the hook should open already in motion.");
let beatCuts = null;
if (a.beats) {
  const grid = JSON.parse(fs.readFileSync(a.beats, "utf8")).beats;
  beatCuts = cuts.filter((c) => grid.some((b) => Math.abs(b * fps - c) <= 2)).length;
  if (cuts.length && beatCuts / cuts.length < 0.5) flags.push(`Only ${beatCuts}/${cuts.length} cuts land on a beat (±2 frames). Snap cuts to beats/downbeats (kit: snapToBeat).`);
}
if (pauses && pauses.length >= 2 && cuts.length && alignedCuts / cuts.length < 0.3) flags.push(`Only ${alignedCuts}/${cuts.length} cuts land on a voice pause. Move cuts to pauses/beats where possible.`);

const report = {
  file,
  size: `${info.width}x${info.height}`,
  fps: Number(fps.toFixed(3)),
  duration: Number((frames.length / fps).toFixed(2)),
  cuts: cuts.map((c) => Number((c / fps).toFixed(2))),
  shots: { count: shots.length, avg: Number((shots.reduce((x, y) => x + y, 0) / shots.length).toFixed(2)), longest: Number((sortedShots.at(-1) ?? 0).toFixed(2)) },
  holdRatio: Number((holdFrames / frames.length).toFixed(2)),
  energyPerSecond: curve,
  energyRaw: energy.map((e) => Number(e.toFixed(4))),
  deadStretches: dead,
  loopSeam: seam,
  pops: pops.map((f) => Number((f / fps).toFixed(2))),
  pauses,
  cutsOnPauses: alignedCuts,
  cutsOnBeats: beatCuts,
  flags,
};

if (a.json) {
  console.log(JSON.stringify(report, null, 2));
} else {
  console.log(`\n${file} · ${report.size} · ${report.fps} fps · ${report.duration} s`);
  console.log(`energy/s  ${curve}`);
  console.log(`cuts      ${report.cuts.length ? report.cuts.join(" · ") + " s" : "none detected"}`);
  console.log(`shots     ${report.shots.count} · avg ${report.shots.avg} s · longest ${report.shots.longest} s`);
  console.log(`holds     ${Math.round(report.holdRatio * 100)}% of frames are calm`);
  if (beatCuts !== null) console.log(`beats     cuts on beats ${beatCuts}/${cuts.length} (±2 frames)`);
  if (seam) console.log(`loop seam ${seam.diff} (neighbouring steps ${seam.typical})`);
  if (pauses) console.log(`pauses    ${pauses.length} in audio · cuts on pauses ${alignedCuts}/${cuts.length}`);
  console.log(flags.length ? `\nFLAGS\n- ${flags.join("\n- ")}` : "\nNo flags. Still watch it once at full speed.");
}
