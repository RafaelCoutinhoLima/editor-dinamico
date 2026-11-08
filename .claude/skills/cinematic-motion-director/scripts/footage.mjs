#!/usr/bin/env node
/**
 * Footage: find, check, download and cut real video (B-roll and sound bites) from YouTube.
 * Run from the Remotion project root. Needs yt-dlp (see `--help` output for install).
 *
 *   node <skill>/scripts/footage.mjs search "como funciona um motor elétrico" --cc --n 8
 *   node <skill>/scripts/footage.mjs fetch <url-or-id>                 # CC only unless --rights …
 *   node <skill>/scripts/footage.mjs moments <id> "rotor,ímã,campo magnético"
 *   node <skill>/scripts/footage.mjs clip <id> 61.2 66.0 --name torque --match public/voice/vo.mp3
 *        # exact cut, re-encoded, audio loudness matched to the voiceover, transcript in clip time
 *   node <skill>/scripts/footage.mjs credits                           # attribution for every clip used
 *   node <skill>/scripts/footage.mjs import ~/Downloads/aula.mp4 --title "Aula" --channel "Meu canal" \
 *        --license "Own footage" [--subs aula.vtt]                    # any file you have rights to
 *
 * Files land in public/broll/<id>/: source.mp4, manifest.json (title, channel, url, license,
 * rights), transcript.json (words + phrases from the video's subtitles), clips/*.mp4.
 *
 * RIGHTS: YouTube's Terms restrict downloading. This tool defaults to videos the uploader
 * licensed under Creative Commons ("reuse allowed") and records attribution. Anything else needs
 * an explicit --rights statement from the user (own channel, written permission, licensed).
 */
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { parseArgs } from "node:util";
import { ffmpegDirForTools, probe, remotionTool } from "./lib/media.mjs";

const { values: a, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    cc: { type: "boolean", default: false },
    n: { type: "string", default: "8" },
    max: { type: "string", default: "1200" }, // max duration (s) for search results
    "max-height": { type: "string", default: "1080" },
    langs: { type: "string", default: "pt.*,en.*" }, // subtitle languages to fetch
    rights: { type: "string" }, // why a non-CC video may be used (user's statement)
    name: { type: "string" },
    window: { type: "string", default: "8" },
    audio: { type: "boolean", default: true },
    loudness: { type: "string", default: "-16" }, // LUFS target for clip audio
    match: { type: "string" }, // voiceover file: measure its loudness and match the clip to it
    dir: { type: "string", default: "public/broll" },
    title: { type: "string" },
    channel: { type: "string" },
    license: { type: "string" },
    url: { type: "string" },
    subs: { type: "string" }, // subtitle file for import (.vtt / .srt / .json3)
  },
});
const [cmd, ...args] = positionals;
const ROOT = process.cwd();
const BROLL = path.resolve(ROOT, a.dir);

const findYtDlp = () => {
  if (process.env.YTDLP) return process.env.YTDLP;
  const local = [".tools/yt-dlp", ".tools/yt-dlp.exe"].map((p) => path.join(ROOT, p)).find((p) => fs.existsSync(p));
  if (local) return local;
  return "yt-dlp"; // PATH
};

const ytdlp = async (argv, { json = false } = {}) => {
  const ffdir = await ffmpegDirForTools();
  const full = ["--js-runtimes", "node", "--no-warnings", ...(ffdir ? ["--ffmpeg-location", ffdir] : []), ...argv];
  return new Promise((resolve, reject) => {
    const p = spawn(findYtDlp(), full, { shell: process.platform === "win32" });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (err += d));
    p.on("error", (e) =>
      reject(
        e.code === "ENOENT"
          ? new Error(
              "yt-dlp not found. Install it once, then re-run:\n" +
                "  • python3 -m pip install -U \"yt-dlp[default]\"\n" +
                "  • or the official binary from https://github.com/yt-dlp/yt-dlp/releases (verify SHA2-256SUMS)\n" +
                "    into .tools/yt-dlp (chmod +x), or set YTDLP=/path/to/yt-dlp",
            )
          : e,
      ),
    );
    p.on("close", (code) => {
      if (code !== 0) {
        if (/confirm you.?re not a bot|Sign in to confirm/i.test(err))
          return reject(
            new Error(
              "YouTube is asking this network to sign in (anti-bot check), so automated download is blocked here.\n" +
                "Don't try to get around it. Options: (1) bring the file yourself and use `footage.mjs import`\n" +
                "(own channel → YouTube Studio download; licensed or CC files you already have); (2) run later or\n" +
                "from another network; (3) use free-licence libraries (Wikimedia Commons, Pexels, Pixabay) via import.",
            ),
          );
        return reject(new Error(`yt-dlp failed (${code}):\n${err.slice(-1200)}`));
      }
      if (!json) return resolve(out);
      resolve(out.split("\n").filter((l) => l.startsWith("{")).map((l) => JSON.parse(l)));
    });
  });
};

const idOf = (s) => (s.match(/(?:v=|youtu\.be\/|shorts\/)([\w-]{11})/) || [, s])[1];
const urlOf = (id) => `https://www.youtube.com/watch?v=${id}`;
const isCC = (lic) => /creative commons/i.test(lic || "");
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");

// ---------- transcript from YouTube subtitles (json3 has word offsets; vtt as fallback) ----------
const parseJson3 = (j) => {
  const words = [];
  for (const ev of j.events || []) {
    if (!ev.segs) continue;
    const t0 = (ev.tStartMs || 0) / 1000;
    const dur = (ev.dDurationMs || 0) / 1000;
    ev.segs.forEach((sg, i) => {
      const text = (sg.utf8 || "").replace(/\n/g, " ").trim();
      if (!text) return;
      const start = t0 + (sg.tOffsetMs || 0) / 1000;
      const next = ev.segs[i + 1];
      const end = next ? t0 + (next.tOffsetMs || 0) / 1000 : t0 + dur;
      for (const w of text.split(/\s+/)) words.push({ text: w, start, end: Math.max(start + 0.05, end) });
    });
  }
  return words;
};
const parseVtt = (txt) => {
  const words = [];
  let last = "";
  for (const block of txt.split(/\n\n+/)) {
    const m = block.match(/(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)/);
    if (!m) continue;
    const t = (h, mm, s) => +h * 3600 + +mm * 60 + +s;
    const start = t(m[1], m[2], m[3]);
    const end = t(m[4], m[5], m[6]);
    const text = block.split("\n").slice(1).join(" ").replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    if (!text || text === last) continue;
    const fresh = text.startsWith(last) ? text.slice(last.length).trim() : text; // rolling auto-captions
    last = text;
    const ws = fresh.split(/\s+/).filter(Boolean);
    ws.forEach((w, i) => words.push({ text: w, start: start + ((end - start) * i) / ws.length, end: start + ((end - start) * (i + 1)) / ws.length }));
  }
  return words;
};
const toPhrases = (words) => {
  const phrases = [];
  let cur = [];
  words.forEach((w, i) => {
    cur.push(w);
    const gap = words[i + 1] ? words[i + 1].start - w.end : 1;
    if (/[.!?…]$/.test(w.text) || gap > 0.6 || cur.length >= 14) {
      phrases.push({ start: cur[0].start, end: w.end, text: cur.map((x) => x.text).join(" ") });
      cur = [];
    }
  });
  return phrases;
};

// ---------------------------------------- commands ----------------------------------------
const search = async () => {
  const q = args.join(" ");
  if (!q) throw new Error('Usage: footage.mjs search "<query>" [--cc] [--n 8]');
  const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}${a.cc ? "&sp=EgIwAQ%253D%253D" : ""}`;
  const flat = await ytdlp(["--flat-playlist", "-j", "--playlist-end", String(Number(a.n) * 2), url], { json: true });
  const picked = flat.filter((v) => !v.duration || v.duration <= Number(a.max)).slice(0, Number(a.n));
  const rows = [];
  let lastError = null;
  for (const v of picked) {
    // Full info per candidate: license, subtitles availability, real duration.
    let info = (await ytdlp(["-j", "--skip-download", urlOf(v.id)], { json: true }).catch((e) => ((lastError = e), [null])))[0];
    if (!info) info = { ...v, license: "unknown — metadata blocked, re-checked on fetch" };
    rows.push({
      id: info.id,
      title: info.title,
      channel: info.channel || info.uploader,
      duration: info.duration,
      views: info.view_count,
      license: info.license || "Standard YouTube License",
      reuse: isCC(info.license),
      subs: Object.keys(info.subtitles || {}).slice(0, 4),
      autoSubs: Object.keys(info.automatic_captions || {}).filter((l) => /^(pt|en)/.test(l)).slice(0, 4),
      url: urlOf(info.id),
    });
  }
  if (lastError) console.log(`(!) Full metadata unavailable for some results: ${lastError.message.split("\n")[0]}\n`);
  fs.mkdirSync(BROLL, { recursive: true });
  fs.writeFileSync(path.join(BROLL, "search.json"), JSON.stringify({ query: q, cc: a.cc, results: rows }, null, 2));
  for (const r of rows)
    console.log(`${r.reuse ? "CC ✓" : "©   "}  ${r.id}  ${fmtTime(r.duration)}  ${String(r.views ?? "?").padStart(8)} views  ${r.channel} — ${r.title}\n      subs: ${r.subs.join(",") || "-"} | auto: ${r.autoSubs.join(",") || "-"}`);
  console.log(`\n→ ${path.relative(ROOT, path.join(BROLL, "search.json"))}  (CC ✓ = uploader allowed reuse with attribution)`);
};

const fetch = async () => {
  const id = idOf(args[0] || "");
  if (!id) throw new Error("Usage: footage.mjs fetch <url-or-id>");
  const [info] = await ytdlp(["-j", "--skip-download", urlOf(id)], { json: true });
  const cc = isCC(info.license);
  if (!cc && !a.rights) {
    throw new Error(
      `"${info.title}" is not Creative Commons (license: ${info.license || "Standard YouTube License"}).\n` +
        "Not downloading. Use a CC video, the user's own footage, or re-run with --rights \"<why you may use it>\"\n" +
        "(e.g. --rights \"own channel\" / \"written permission from <name>, <date>\").",
    );
  }
  const dir = path.join(BROLL, id);
  fs.mkdirSync(dir, { recursive: true });
  const h = Number(a["max-height"]);
  // H.264 + AAC first: Remotion decodes it everywhere and the bundled ffmpeg can merge it.
  const format = `bv*[height<=${h}][vcodec^=avc1]+ba[ext=m4a]/b[height<=${h}][ext=mp4]/bv*[height<=${h}]+ba/b[height<=${h}]/b`;
  await ytdlp(["-f", format, "--merge-output-format", "mp4", "-o", path.join(dir, "source.%(ext)s"), "--no-playlist", urlOf(id)]);
  await ytdlp(["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", a.langs, "--sub-format", "json3/vtt/best", "-o", path.join(dir, "subs.%(ext)s"), urlOf(id)]).catch(() => null);

  // Transcript: prefer manual subs over auto, json3 over vtt.
  const subFiles = fs.readdirSync(dir).filter((f) => f.startsWith("subs.") && /\.(json3|vtt)$/.test(f));
  const rank = (f) => (/\.json3$/.test(f) ? 0 : 1) + (/-orig|\.pt/.test(f) ? 0 : 0.5);
  subFiles.sort((x, y) => rank(x) - rank(y));
  let words = [];
  if (subFiles[0]) {
    const raw = fs.readFileSync(path.join(dir, subFiles[0]), "utf8");
    words = subFiles[0].endsWith(".json3") ? parseJson3(JSON.parse(raw)) : parseVtt(raw);
  }
  fs.writeFileSync(path.join(dir, "transcript.json"), JSON.stringify({ source: subFiles[0] || null, words, phrases: toPhrases(words) }, null, 2));

  const manifest = {
    id,
    url: urlOf(id),
    title: info.title,
    channel: info.channel || info.uploader,
    channelUrl: info.channel_url || info.uploader_url,
    license: info.license || "Standard YouTube License",
    rights: cc ? "Creative Commons (reuse allowed) — attribution required" : a.rights,
    duration: info.duration,
    width: info.width,
    height: info.height,
    fetchedAt: new Date().toISOString(),
    source: `broll/${id}/source.mp4`,
    clips: [],
  };
  fs.writeFileSync(path.join(dir, "manifest.json"), JSON.stringify(manifest, null, 2));
  const size = fs.statSync(path.join(dir, "source.mp4")).size;
  console.log(`✓ ${manifest.channel} — ${manifest.title}\n  ${manifest.license} · ${fmtTime(manifest.duration)} · ${(size / 1e6).toFixed(1)} MB`);
  console.log(`  transcript: ${words.length} words from ${subFiles[0] || "no subtitles (transcribe with voice-map.mjs --whisper if needed)"}`);
  console.log(`  → ${path.relative(ROOT, dir)}/`);
};

const moments = () => {
  const id = idOf(args[0] || "");
  const kws = (args[1] || "").split(",").map((k) => norm(k.trim())).filter(Boolean);
  if (!id || !kws.length) throw new Error('Usage: footage.mjs moments <id> "kw1,kw2"');
  const t = JSON.parse(fs.readFileSync(path.join(BROLL, id, "transcript.json"), "utf8"));
  const win = Number(a.window);
  // Score each phrase by keyword hits, then grow it into a clip window aligned to phrase edges.
  const scored = t.phrases
    .map((p, i) => ({ ...p, i, hits: kws.filter((k) => norm(p.text).includes(k)) }))
    .filter((p) => p.hits.length)
    .sort((x, y) => y.hits.length - x.hits.length || x.start - y.start);
  const seen = new Set();
  const out = [];
  for (const p of scored) {
    if (seen.has(p.i)) continue;
    let s = p.i;
    let e = p.i;
    while (t.phrases[e + 1] && t.phrases[e + 1].end - t.phrases[s].start <= win) e++;
    while (t.phrases[s - 1] && t.phrases[e].end - t.phrases[s - 1].start <= win && s > p.i - 1) s--;
    for (let k = s; k <= e; k++) seen.add(k);
    out.push({ start: +t.phrases[s].start.toFixed(2), end: +t.phrases[e].end.toFixed(2), hits: p.hits, text: t.phrases.slice(s, e + 1).map((x) => x.text).join(" ") });
    if (out.length >= 8) break;
  }
  if (!out.length) console.log("No phrase matches those keywords. Try synonyms, English terms, or open transcript.json.");
  out.forEach((m, k) => console.log(`#${k + 1}  ${fmtTime(m.start)}–${fmtTime(m.end)}  (${m.start}–${m.end} s)  [${m.hits.join(", ")}]\n    “${m.text}”`));
};

const clip = async () => {
  const id = idOf(args[0] || "");
  const [start, end] = [Number(args[1]), Number(args[2])];
  if (!id || !(end > start)) throw new Error("Usage: footage.mjs clip <id> <start s> <end s> [--name x]");
  const dir = path.join(BROLL, id);
  const manifestPath = path.join(dir, "manifest.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const name = (a.name || `${start.toFixed(1)}-${end.toFixed(1)}`).replace(/[^\w.-]+/g, "-");
  fs.mkdirSync(path.join(dir, "clips"), { recursive: true });
  const out = path.join(dir, "clips", `${name}.mp4`);
  let target = Number(a.loudness);
  if (a.match) {
    // Loudness of the voiceover's SPEECH only (pauses excluded — integrated loudness over the whole
    // file reads ~3 LU low for paused narration), so sound bites sit at the same perceived level.
    const { silences, probeAudio } = await import("./lib/media.mjs");
    const { duration } = await probeAudio(a.match);
    const quiet = await silences(a.match, -40, 0.2);
    const speech = [];
    let t = 0;
    for (const q of quiet) (q.start - t > 0.2 && speech.push([t, q.start]), (t = q.end));
    if (duration - t > 0.2) speech.push([t, duration]);
    const parts = speech.slice(0, 60).map(([s0, e0], i) => `[0:a]atrim=${s0}:${e0},asetpts=PTS-STARTPTS[s${i}]`);
    // Mono VO (ElevenLabs exports mono) is played on BOTH channels of the stereo render, which reads
    // +3 LU louder than the file itself — measure it the way it will sound in the mix.
    const { stdout: chOut } = await remotionTool("ffprobe", ["-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of", "csv=p=0", a.match]);
    const toStereo = Number(chOut.trim()) === 1 ? ",pan=stereo|c0=c0|c1=c0" : "";
    const graph = `${parts.join(";")};${speech.slice(0, 60).map((_, i) => `[s${i}]`).join("")}concat=n=${Math.min(60, speech.length)}:v=0:a=1${toStereo},loudnorm=print_format=json`;
    const { stderr } = await remotionTool("ffmpeg", ["-i", a.match, "-filter_complex", graph, "-f", "null", "-"]);
    const m = stderr.match(/"input_i"\s*:\s*"(-?[\d.]+)"/);
    if (m) target = Math.round(Number(m[1]) * 10) / 10;
  }
  // Re-encode: frame-exact in/out points, every frame a fast seek target for Remotion.
  await remotionTool("ffmpeg", ["-y", "-loglevel", "error", "-ss", String(start), "-i", path.join(dir, "source.mp4"), "-t", String(end - start), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", ...(a.audio ? ["-af", `loudnorm=I=${target}:TP=-1.5:LRA=11`, "-ar", "48000", "-c:a", "aac", "-b:a", "160k"] : ["-an"]), "-movflags", "+faststart", out]);
  // Transcript in CLIP time, so captions line up when the clip is used as a sound bite.
  const tPath = path.join(dir, "transcript.json");
  if (fs.existsSync(tPath)) {
    const t = JSON.parse(fs.readFileSync(tPath, "utf8"));
    const words = t.words.filter((w) => w.start >= start - 0.05 && w.start < end).map((w) => ({ text: w.text, start: +(w.start - start).toFixed(3), end: +(Math.min(w.end, end) - start).toFixed(3) }));
    fs.writeFileSync(path.join(dir, "clips", `${name}.transcript.json`), JSON.stringify({ source: t.source, clip: [start, end], words, phrases: toPhrases(words) }, null, 2));
  }
  manifest.clips = manifest.clips.filter((c) => c.name !== name).concat({ name, start, end, file: `broll/${id}/clips/${name}.mp4`, transcript: `broll/${id}/clips/${name}.transcript.json` });
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`✓ ${path.relative(ROOT, out)} (${(end - start).toFixed(2)} s, audio at ${target} LUFS${a.match ? " = voiceover" : ""}) — credit: ${manifest.channel} (${manifest.license})`);
};

const credits = () => {
  if (!fs.existsSync(BROLL)) return console.log("No footage yet.");
  const list = fs
    .readdirSync(BROLL)
    .map((d) => path.join(BROLL, d, "manifest.json"))
    .filter((p) => fs.existsSync(p))
    .map((p) => JSON.parse(fs.readFileSync(p, "utf8")));
  const lines = list.map((m) => `“${m.title}” — ${m.channel}${m.url ? ` (${m.url})` : ""} · ${m.license}${m.rights && m.rights !== m.license && !isCC(m.license) ? ` · ${m.rights}` : ""}`);
  fs.writeFileSync(path.join(BROLL, "credits.json"), JSON.stringify(list.map((m) => ({ id: m.id, title: m.title, channel: m.channel, url: m.url, license: m.license, rights: m.rights, onScreen: `${m.channel} · YouTube${isCC(m.license) ? " (CC BY)" : ""}` })), null, 2));
  console.log(lines.join("\n") || "No manifests found.");
  console.log(`\n→ ${path.relative(ROOT, path.join(BROLL, "credits.json"))} — put these in the description and the on-screen source tag.`);
};

const parseSrtOrVtt = (txt) => parseVtt(txt.replace(/(\d+:\d+:\d+),(\d+)/g, "$1.$2"));

const importFile = async () => {
  const file = args[0];
  if (!file || !fs.existsSync(file)) throw new Error('Usage: footage.mjs import <file> --title "…" --channel "…" --license "…" [--subs f.vtt|.srt|.json3] [--url …]');
  if (!a.license) throw new Error('Say what rights you have: --license "Own footage" | "CC BY 4.0" | "Licensed from <x>" …');
  const id = (a.title || path.basename(file, path.extname(file))).toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  const dir = path.join(BROLL, id);
  fs.mkdirSync(dir, { recursive: true });
  const dest = path.join(dir, "source.mp4");
  if (/\.mp4$/i.test(file)) fs.copyFileSync(file, dest);
  else await remotionTool("ffmpeg", ["-y", "-loglevel", "error", "-i", file, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", dest]);
  let words = [];
  if (a.subs) {
    const raw = fs.readFileSync(a.subs, "utf8");
    words = a.subs.endsWith(".json3") ? parseJson3(JSON.parse(raw)) : parseSrtOrVtt(raw);
  }
  fs.writeFileSync(path.join(dir, "transcript.json"), JSON.stringify({ source: a.subs ? path.basename(a.subs) : null, words, phrases: toPhrases(words) }, null, 2));
  const info = await probe(dest);
  const manifest = { id, url: a.url || null, title: a.title || id, channel: a.channel || "—", channelUrl: null, license: a.license, rights: a.rights || a.license, duration: info.duration, width: info.width, height: info.height, fetchedAt: new Date().toISOString(), source: `broll/${id}/source.mp4`, clips: [] };
  fs.writeFileSync(path.join(dir, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log(`✓ imported ${manifest.title} (${manifest.license}) · ${info.duration.toFixed(1)} s · ${words.length} transcript words\n  → ${path.relative(ROOT, dir)}/  (id: ${id})`);
};

const commands = { search, fetch, moments, clip, credits, import: importFile };
if (!commands[cmd]) {
  console.log("Commands: search | fetch | moments | clip | credits | import   (see the header of this file)");
  process.exit(cmd ? 1 : 0);
}
try {
  await commands[cmd]();
} catch (e) {
  console.error(e.message);
  process.exit(1);
}
