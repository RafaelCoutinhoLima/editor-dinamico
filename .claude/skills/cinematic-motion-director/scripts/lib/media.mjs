// Zero-dependency media helpers built on the ffmpeg/ffprobe that ship with Remotion
// (`npx remotion ffmpeg`). That build is minimal (no rawvideo muxer, no tile/fps filters),
// so frames are piped as raw pixels through image2pipe and composed in Node.
import { spawn } from "node:child_process";
import zlib from "node:zlib";

const NPX = process.platform === "win32" ? "npx.cmd" : "npx";

const run = (tool, args, { binary = false } = {}) =>
  new Promise((resolve, reject) => {
    const p = spawn(NPX, ["remotion", tool, "-hide_banner", ...args], { shell: process.platform === "win32" });
    const out = [];
    let err = "";
    p.stdout.on("data", (d) => out.push(d));
    p.stderr.on("data", (d) => (err += d));
    p.on("error", reject);
    p.on("close", (code) => {
      if (code !== 0) return reject(new Error(`remotion ${tool} failed (${code}):\n${err.slice(-800)}`));
      resolve({ stdout: binary ? Buffer.concat(out) : Buffer.concat(out).toString(), stderr: err });
    });
  });

/** { width, height, fps, duration, hasAudio } of a video file. */
export const probe = async (file) => {
  const { stdout } = await run("ffprobe", ["-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", file]);
  const j = JSON.parse(stdout);
  const v = j.streams.find((s) => s.codec_type === "video");
  const [n, d] = v.r_frame_rate.split("/").map(Number);
  return { width: v.width, height: v.height, fps: n / d, duration: Number(j.format.duration), hasAudio: j.streams.some((s) => s.codec_type === "audio") };
};

/** Every frame of `file` scaled to w×h, as one Buffer per frame. pixFmt: "gray" | "rgb24". */
export const rawFrames = async (file, w, h, pixFmt = "gray") => {
  const { stdout } = await run("ffmpeg", ["-loglevel", "error", "-i", file, "-vf", `scale=${w}:${h}`, "-pix_fmt", pixFmt, "-c:v", "rawvideo", "-f", "image2pipe", "-"], { binary: true });
  const size = w * h * (pixFmt === "gray" ? 1 : 3);
  const frames = [];
  for (let o = 0; o + size <= stdout.length; o += size) frames.push(stdout.subarray(o, o + size));
  return frames;
};

/** Mono audio as Float32Array in [-1, 1] at `sampleRate` (any format ffmpeg can read). */
export const decodeMono = async (file, sampleRate = 11025) => {
  const { stdout } = await run("ffmpeg", ["-loglevel", "error", "-i", file, "-vn", "-ac", "1", "-ar", String(sampleRate), "-c:a", "pcm_s16le", "-f", "wav", "-"], { binary: true });
  // Piped WAV has no reliable sizes: find the "data" chunk and read to the end.
  let o = 12;
  while (o + 8 <= stdout.length && stdout.toString("ascii", o, o + 4) !== "data") o += 8 + stdout.readUInt32LE(o + 4);
  const pcm = stdout.subarray(o + 8);
  const out = new Float32Array(Math.floor(pcm.length / 2));
  for (let i = 0; i < out.length; i++) out[i] = pcm.readInt16LE(i * 2) / 32768;
  return out;
};

/** Silence intervals [{start, end}] in seconds, via ffmpeg silencedetect. */
export const silences = async (file, noiseDb = -35, minSeconds = 0.25) => {
  const { stderr } = await run("ffmpeg", ["-i", file, "-vn", "-af", `silencedetect=noise=${noiseDb}dB:d=${minSeconds}`, "-f", "null", "-"]);
  const out = [];
  let start = null;
  for (const line of stderr.split("\n")) {
    const s = line.match(/silence_start: ([\d.]+)/);
    const e = line.match(/silence_end: ([\d.]+)/);
    if (s) start = Number(s[1]);
    if (e && start !== null) (out.push({ start, end: Number(e[1]) }), (start = null));
  }
  return out;
};

const CRC = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc32 = (buf) => {
  let c = 0xffffffff;
  for (const b of buf) c = CRC[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
const chunk = (type, data) => {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
};

/** Encode an RGB24 buffer as PNG. */
export const encodePng = (rgb, width, height) => {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type RGB
  const rows = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y++) rgb.copy(rows, y * (width * 3 + 1) + 1, y * width * 3, (y + 1) * width * 3);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(rows)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
};

/** Lay out equally sized RGB24 tiles in a grid with a dark gutter. Returns PNG bytes. */
export const contactSheet = (tiles, tileW, tileH, cols, gap = 8, bg = [20, 20, 22]) => {
  const rows = Math.ceil(tiles.length / cols);
  const W = cols * tileW + (cols + 1) * gap;
  const H = rows * tileH + (rows + 1) * gap;
  const img = Buffer.alloc(W * H * 3);
  for (let i = 0; i < W * H; i++) img.set(bg, i * 3);
  tiles.forEach((t, i) => {
    const x0 = gap + (i % cols) * (tileW + gap);
    const y0 = gap + Math.floor(i / cols) * (tileH + gap);
    for (let y = 0; y < tileH; y++) t.copy(img, ((y0 + y) * W + x0) * 3, y * tileW * 3, (y + 1) * tileW * 3);
  });
  return encodePng(img, W, H);
};

/** Decode any image/video file's first frame to RGB24 at w×h. */
export const decodeImage = async (file, w, h) => (await rawFrames(file, w, h, "rgb24"))[0];

/**
 * Directory with `ffmpeg` / `ffprobe` that external tools (yt-dlp) can call directly.
 * Uses the binaries bundled with Remotion; on macOS/Linux they need their shared libraries on the
 * library path, so tiny wrapper scripts are written to a temp dir. Returns null if not found.
 */
export const ffmpegDirForTools = async () => {
  const fs = await import("node:fs");
  const os = await import("node:os");
  const path = await import("node:path");
  const base = path.join(process.cwd(), "node_modules", "@remotion");
  if (!fs.existsSync(base)) return null;
  const dir = fs.readdirSync(base).find((d) => d.startsWith("compositor-") && fs.existsSync(path.join(base, d, process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg")));
  if (!dir) return null;
  const real = path.join(base, dir);
  if (process.platform === "win32") return real; // DLLs next to the .exe are found automatically
  const wrap = path.join(os.tmpdir(), "remotion-ffmpeg-wrappers");
  fs.mkdirSync(wrap, { recursive: true });
  const libVar = process.platform === "darwin" ? "DYLD_LIBRARY_PATH" : "LD_LIBRARY_PATH";
  for (const tool of ["ffmpeg", "ffprobe"]) {
    const p = path.join(wrap, tool);
    fs.writeFileSync(p, `#!/bin/sh\n${libVar}="${real}" exec "${path.join(real, tool)}" "$@"\n`);
    fs.chmodSync(p, 0o755);
  }
  return wrap;
};

export { run as remotionTool };

/** { duration } of any audio (or video) file, in seconds. */
export const probeAudio = async (file) => {
  const { stdout } = await run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "json", file]);
  return { duration: Number(JSON.parse(stdout).format.duration) };
};
