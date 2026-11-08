// Layout engine: decides ONCE (pure function of the props) where every overlay goes, so that
//  - nothing sits in the platform UI bands (9:16: top 220 px, bottom 320 px at 1080x1920),
//  - nothing in front of the video covers the head (face track from edin, union over the window),
//  - overlays that share screen time never overlap each other or the caption band.
// If an overlay only fits on top of the caption band, captions hide during that overlay.
import type { EdinProps, FaceSample, Overlay } from "./types";

export type Rect = { x: number; y: number; w: number; h: number };
export type Placed = Rect & { scale: number; hideCaptions: boolean; fontSize: number };
export type Layout = {
  unit: number; // 1 px of the 1080-wide design, scaled to this composition
  safe: { top: number; bottom: number; side: number };
  band: Rect; // caption band
  captionWindows: [number, number][];
  placed: (Placed | null)[]; // same order as props.overlays (null for caption-pill)
  warnings: string[];
};

const DEFAULT_FACE: FaceSample = { t: 0, x: 0.5, y: 0.4, size: 0.16 };

/** Face (normalised) at time t: linear interpolation between samples, holds the nearest outside. */
export const faceAt = (track: FaceSample[], t: number): FaceSample => {
  if (!track.length) return DEFAULT_FACE;
  if (t <= track[0].t) return track[0];
  const last = track[track.length - 1];
  if (t >= last.t) return last;
  let lo = 0;
  let hi = track.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (track[mid].t <= t) lo = mid;
    else hi = mid;
  }
  const a = track[lo];
  const b = track[hi];
  // a gap > 1.5 s means the face was lost: hold the previous sample instead of sliding
  if (b.t - a.t > 1.5) return a;
  const k = (t - a.t) / (b.t - a.t);
  return { t, x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, size: a.size + (b.size - a.size) * k };
};

/**
 * Head in px for one face sample. edin's face_track stores the YuNet box height as `size`
 * (forehead to chin, ~0.9 x as wide). "head" adds hair and ears; "core" is the face itself
 * (eyes, nose, mouth, chin), the part that may never be covered even as a last resort.
 */
export const headBox = (f: FaceSample, W: number, H: number, part: "head" | "core" = "head"): Rect => {
  const fh = f.size * H;
  const cx = f.x * W;
  const cy = f.y * H;
  return part === "head"
    ? { x: cx - 0.75 * fh, y: cy - 0.9 * fh, w: 1.5 * fh, h: 1.45 * fh }
    : { x: cx - 0.5 * fh, y: cy - 0.6 * fh, w: 1.0 * fh, h: 1.15 * fh };
};

const union = (a: Rect, b: Rect): Rect => {
  const x = Math.min(a.x, b.x);
  const y = Math.min(a.y, b.y);
  return { x, y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y };
};

export const intersects = (a: Rect, b: Rect, pad = 0) =>
  a.x < b.x + b.w + pad && a.x + a.w + pad > b.x && a.y < b.y + b.h + pad && a.y + a.h + pad > b.y;

/** Union of the head boxes over [s, e] (samples inside the window, or the interpolated ends). */
export const headUnion = (track: FaceSample[], s: number, e: number, W: number, H: number, part: "head" | "core" = "head"): Rect => {
  let r = headBox(faceAt(track, s), W, H, part);
  r = union(r, headBox(faceAt(track, e), W, H, part));
  for (const f of track) if (f.t >= s && f.t <= e) r = union(r, headBox(f, W, H, part));
  return r;
};

const overlapsInTime = (a: Overlay, b: Overlay, pad = 0.15) => a.start < b.end + pad && b.start < a.end + pad;

// ---------------------------------------------------------------- size estimates (shared with renderers)

/** Average glyph width in em: Anton is condensed, Montserrat ExtraBold is wide. */
export const GLYPH = { anton: 0.5, montserrat: 0.68 };

/** Greedy word wrap with an estimated glyph width; returns the lines. */
export const wrap = (text: string, fontSize: number, maxW: number, em: number): string[] => {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (cur && next.length * em * fontSize > maxW) {
      lines.push(cur);
      cur = w;
    } else cur = next;
  }
  if (cur) lines.push(cur);
  return lines;
};

type Size = { w: number; h: number; fontSize: number };

export const sizeOf = (o: Overlay, u: number, W: number, scale = 1): Size | null => {
  const maxW = W - 120 * u;
  switch (o.type) {
    case "behind-head-word": {
      const len = Math.max(1, o.text.length);
      const fs = Math.min((o.size ?? 300) * u, maxW / (GLYPH.anton * len)) * scale;
      return { w: Math.min(maxW, len * GLYPH.anton * fs * 1.05), h: fs * 1.05, fontSize: fs };
    }
    case "kinetic-title": {
      let fs = 104 * u * scale;
      let lines = wrap(o.text.toUpperCase(), fs, maxW, GLYPH.anton);
      while (lines.length > 3 && fs > 56 * u) {
        fs *= 0.9;
        lines = wrap(o.text.toUpperCase(), fs, maxW, GLYPH.anton);
      }
      const w = Math.min(maxW, Math.max(...lines.map((l) => l.length)) * GLYPH.anton * fs + 20 * u);
      return { w, h: lines.length * fs * 1.08 + 16 * u, fontSize: fs };
    }
    case "card": {
      const w = Math.min(maxW, 600 * u * scale);
      const inner = w - 2 * 36 * u * scale;
      const tfs = 46 * u * scale;
      const bfs = 32 * u * scale;
      const tl = wrap(o.title, tfs, inner, GLYPH.montserrat).length;
      const bl = o.body ? wrap(o.body, bfs, inner, GLYPH.montserrat * 0.92).length : 0;
      const h = (2 * 32 + (o.kicker ? 44 : 0)) * u * scale + tl * tfs * 1.18 + (bl ? 14 * u * scale + bl * bfs * 1.3 : 0);
      return { w, h, fontSize: tfs };
    }
    case "checklist": {
      const w = Math.min(maxW, 800 * u * scale);
      const rfs = 40 * u * scale;
      const inner = w - (2 * 36 + 76) * u * scale;
      const rows = o.items.reduce((n, it) => n + wrap(it.text, rfs, inner, GLYPH.montserrat).length, 0);
      const h = (2 * 32 + (o.title ? 72 : 0)) * u * scale + rows * rfs * 1.3 + o.items.length * 30 * u * scale;
      return { w, h, fontSize: rfs };
    }
    case "lower-third": {
      const fs = 64 * u * scale;
      const nameW = o.name.length * GLYPH.anton * fs;
      const roleW = (o.role ?? "").length * GLYPH.montserrat * 30 * u * scale;
      const w = Math.min(maxW, Math.max(nameW, roleW) + 90 * u * scale);
      return { w, h: (o.role ? 150 : 110) * u * scale, fontSize: fs };
    }
    default:
      return null;
  }
};

// ---------------------------------------------------------------- placement

const candidates = (o: Overlay, s: Size, head: Rect, W: number, H: number, safe: Layout["safe"], u: number): { x: number; y: number }[] => {
  const gap = 36 * u;
  const cx = head.x + head.w / 2;
  const cy = head.y + head.h / 2;
  const centerX = (W - s.w) / 2;
  const clampX = (x: number) => Math.max(safe.side, Math.min(W - safe.side - s.w, x));
  const above = { x: clampX(cx - s.w / 2), y: head.y - gap - s.h };
  const aboveCentered = { x: centerX, y: head.y - gap - s.h };
  const below = { x: clampX(cx - s.w / 2), y: head.y + head.h + gap };
  const belowCentered = { x: centerX, y: head.y + head.h + gap };
  const right = { x: head.x + head.w + gap, y: cy - s.h / 2 };
  const left = { x: head.x - gap - s.w, y: cy - s.h / 2 };
  const topSafe = { x: centerX, y: safe.top + 10 * u };
  const bottomLeft = { x: safe.side, y: H - safe.bottom - s.h - 20 * u };
  const pref: Record<Overlay["type"], { x: number; y: number }[]> = {
    "behind-head-word": [],
    "kinetic-title": [aboveCentered, topSafe, above, belowCentered],
    card: [right, left, above, below, topSafe],
    checklist: [belowCentered, below, aboveCentered, topSafe],
    "lower-third": [bottomLeft, { x: safe.side, y: head.y + head.h + gap }],
    "caption-pill": [],
  };
  const first = pref[o.type][0] ?? { x: centerX, y: H / 2 };
  // fallback scan of the whole safe area, nearest to the preferred spot first
  const scan: { x: number; y: number }[] = [];
  for (let y = safe.top; y + s.h <= H - safe.bottom; y += 16 * u)
    for (const x of [centerX, safe.side, W - safe.side - s.w]) scan.push({ x, y });
  scan.sort((a, b) => Math.hypot(a.x - first.x, a.y - first.y) - Math.hypot(b.x - first.x, b.y - first.y));
  return [...pref[o.type], ...scan];
};

export const computeLayout = (p: EdinProps): Layout => {
  const W = p.width;
  const H = p.height;
  const u = Math.min(W, H) / 1080;
  const vertical = H / W > 1.5;
  const safe = vertical
    ? { top: (220 / 1920) * H, bottom: (320 / 1920) * H, side: 60 * u }
    : { top: 0.06 * H, bottom: 0.08 * H, side: 60 * u };
  const warnings: string[] = [];

  // caption band: just below the head (90th percentile of head bottoms), above the bottom UI band
  const caps = p.overlays.filter((o) => o.type === "caption-pill");
  const captionWindows: [number, number][] = caps.map((c) => [c.start, c.end]);
  const bandH = 130 * u;
  const bottoms = (p.face.length ? p.face : [DEFAULT_FACE]).map((f) => {
    const b = headBox(f, W, H);
    return b.y + b.h;
  }).sort((a, b) => a - b);
  const p90 = bottoms[Math.min(bottoms.length - 1, Math.floor(bottoms.length * 0.9))];
  const bandTop = Math.min(H - safe.bottom - bandH - 10 * u, Math.max(H * 0.52, p90 + 30 * u));
  const band: Rect = { x: safe.side, y: bandTop, w: W - 2 * safe.side, h: bandH };

  const capActive = (o: Overlay) => captionWindows.some(([s, e]) => o.start < e && s < o.end);
  const placed: (Placed | null)[] = p.overlays.map(() => null);
  const insideSafe = (r: Rect) =>
    r.x >= safe.side - 0.5 && r.x + r.w <= W - safe.side + 0.5 && r.y >= safe.top - 0.5 && r.y + r.h <= H - safe.bottom + 0.5;

  // anchored words first (their spot is dictated by the head), then the rest in plan order
  const order = p.overlays.map((_, i) => i).sort((a, b) => {
    const rank = (i: number) => (p.overlays[i].type === "behind-head-word" ? 0 : 1);
    return rank(a) - rank(b) || a - b;
  });
  order.forEach((idx) => {
    const o = p.overlays[idx];
    if (o.type === "caption-pill") return;
    const head = headUnion(p.face, o.start, o.end, W, H);
    const others = p.overlays
      .map((q, j) => ({ q, r: placed[j] }))
      .filter(({ q, r }) => r && overlapsInTime(o, q))
      .map(({ r }) => r as Placed);

    if (o.type === "behind-head-word") {
      // anchored to the head: centred on it, top of the word around the forehead, inside the safe area
      const s = sizeOf(o, u, W)!;
      const cx = head.x + head.w / 2;
      const x = Math.max(safe.side, Math.min(W - safe.side - s.w, cx - s.w / 2));
      // the lower ~70 % of the word hides behind the hair/forehead, the top peeks out above the head
      let y = Math.max(safe.top, head.y - s.h * 0.3);
      y = Math.min(y, H - safe.bottom - s.h);
      placed[idx] = { x, y, w: s.w, h: s.h, scale: 1, hideCaptions: false, fontSize: s.fontSize };
      return;
    }

    // pass 1 keeps clear of the whole head (hair included); pass 2 only of the face itself
    const core = headUnion(p.face, o.start, o.end, W, H, "core");
    let result: Placed | null = null;
    for (const avoid of [head, core]) {
      for (const scale of [1, 0.88, 0.76, 0.66]) {
        const s = sizeOf(o, u, W, scale)!;
        for (const withBand of [true, false]) {
          const blockers = [...others, ...(withBand && capActive(o) ? [band] : [])];
          for (const c of candidates(o, s, head, W, H, safe, u)) {
            const r = { x: c.x, y: c.y, w: s.w, h: s.h };
            if (!insideSafe(r) || intersects(r, avoid, 8 * u) || blockers.some((b) => intersects(r, b, 16 * u))) continue;
            result = { ...r, scale, fontSize: s.fontSize, hideCaptions: !withBand && capActive(o) };
            break;
          }
          if (result) break;
        }
        if (result) break;
      }
      if (result) break;
    }
    if (!result) {
      // no spot that is off the face, off the other overlays and inside the safe area: skip it
      // rather than break the "never overlap / never cover the face" rules
      warnings.push(`overlay #${idx} (${o.type}) skipped: no free spot (too many overlays at once for this framing)`);
      return;
    }
    placed[idx] = result;
  });
  return { unit: u, safe, band, captionWindows, placed, warnings };
};
