// Pill captions: 1-3 words per page, uppercase, active word in the accent, dark translucent pill.
// Pages never mix phrases (edin's `blk`), break on pauses, and sit in the caption band from layout.ts.
import React, { useMemo } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { BODY } from "./fonts";
import type { Rect } from "./layout";
import type { CaptionPill, Word } from "./types";

type Page = { words: Word[]; start: number; end: number };

export const buildPages = (words: Word[], perPage = 3, maxChars = 20, maxGap = 0.4): Page[] => {
  const pages: Page[] = [];
  let cur: Word[] = [];
  const flush = () => {
    if (cur.length) pages.push({ words: cur, start: cur[0].s, end: cur[cur.length - 1].e });
    cur = [];
  };
  for (const w of words) {
    const prev = cur[cur.length - 1];
    const chars = cur.reduce((n, x) => n + x.w.length + 1, 0) + w.w.length;
    if (prev && (w.blk !== prev.blk || w.s - prev.e > maxGap || cur.length >= perPage || chars > maxChars)) flush();
    cur.push(w);
  }
  flush();
  // each page holds until the next one starts (max 0.6 s after its last word)
  pages.forEach((p, i) => {
    const next = pages[i + 1];
    p.end = Math.min(next ? next.start : Infinity, p.end + 0.6);
  });
  return pages;
};

export const Captions: React.FC<{
  words: Word[];
  cfg: CaptionPill[];
  band: Rect;
  accent: string;
  u: number;
  hidden: (t: number) => boolean;
}> = ({ words, cfg, band, accent, u, hidden }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const c = cfg.find((x) => t >= x.start && t < x.end);
  const pages = useMemo(() => buildPages(words, cfg[0]?.wordsPerPage ?? 3), [words, cfg]);
  if (!c || hidden(t)) return null;
  const page = pages.find((p) => t >= p.start && t < p.end);
  if (!page) return null;
  const emph = new Set(c.emphasis ?? []);
  const local = (t - page.start) * fps;
  const pop = interpolate(local, [0, 3, 6], [0.86, 1.04, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fs = 64 * u;
  return (
    <div
      style={{
        position: "absolute",
        left: band.x,
        width: band.w,
        top: band.y,
        height: band.h,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "rgba(8,8,10,0.72)",
          borderRadius: 999,
          padding: `${14 * u}px ${36 * u}px`,
          scale: String(pop),
          maxWidth: band.w,
          display: "flex",
          gap: 18 * u,
          whiteSpace: "nowrap",
        }}
      >
        {page.words.map((w) => {
          const active = t >= w.s && t < w.e + 0.05;
          const color = emph.has(w.i) || active ? accent : "white";
          return (
            <span
              key={w.i}
              style={{
                fontFamily: BODY,
                fontWeight: 800,
                fontSize: fs,
                lineHeight: 1.15,
                color,
                textTransform: c.uppercase === false ? "none" : "uppercase",
                opacity: t >= w.s - 0.02 ? 1 : 0.55,
              }}
            >
              {w.w.replace(/[.,!?;:…]+$/u, "")}
            </span>
          );
        })}
      </div>
    </div>
  );
};
