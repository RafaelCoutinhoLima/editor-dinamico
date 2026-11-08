// Overlay renderers. Each one is mounted inside a <Sequence> that starts at the overlay's start,
// so useCurrentFrame() is local (0 = start). Position and size come from layout.ts.
import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { ease, fxWindow, mix, progress, WordStagger } from "./motion";
import { BODY, DISPLAY } from "./fonts";
import { faceAt, wrap, GLYPH, type Placed } from "./layout";
import type { BehindHeadWord, Card, Checklist, FaceSample, KineticTitle, LowerThird } from "./types";

type Base<T> = { o: T; r: Placed; accent: string; u: number };

const useWindow = (start: number, end: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = Math.max(2, Math.round((end - start) * fps));
  return { frame, fps, len, env: fxWindow(frame, 0, len, 8, 8) };
};

const box = (r: Placed): React.CSSProperties => ({ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h });

const SHADOW = "0 6px 30px rgba(0,0,0,0.45)";
const GLASS: React.CSSProperties = {
  background: "rgba(14,16,20,0.74)",
  backdropFilter: "blur(18px)",
  border: "1px solid rgba(255,255,255,0.28)",
  boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
};

// ---------------------------------------------------------------- behind-head word

/** SVG mask (data URL) that hides the word where the head and shoulders are: used when there is no person cutout. */
const headMask = (f: FaceSample, W: number, H: number) => {
  const fh = f.size * H;
  const cx = f.x * W;
  const cy = f.y * H;
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='${W}' height='${H}' viewBox='0 0 ${W} ${H}'>` +
    `<defs><filter id='b'><feGaussianBlur stdDeviation='${(fh * 0.06).toFixed(1)}'/></filter>` +
    `<mask id='m'><rect width='${W}' height='${H}' fill='white'/><g filter='url(#b)' fill='black'>` +
    `<ellipse cx='${cx}' cy='${cy - 0.12 * fh}' rx='${0.8 * fh}' ry='${0.86 * fh}'/>` +
    `<rect x='${cx - 0.42 * fh}' y='${cy + 0.4 * fh}' width='${0.84 * fh}' height='${0.9 * fh}'/>` +
    `<rect x='${cx - 1.6 * fh}' y='${cy + 1.15 * fh}' width='${3.2 * fh}' height='${H}' rx='${0.7 * fh}'/>` +
    `</g></mask></defs><rect width='${W}' height='${H}' fill='black' mask='url(#m)'/></svg>`;
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
};

export const BehindWord: React.FC<Base<BehindHeadWord> & { face: FaceSample[]; masked: boolean }> = ({ o, r, accent, u, face, masked }) => {
  const { frame, fps, len, env } = useWindow(o.start, o.end);
  const { width: W, height: H } = useVideoConfig();
  const t = progress(frame, 0, 14, ease.out);
  const out = progress(frame, len - 8, 8, ease.in);
  const mask = masked ? headMask(faceAt(face, o.start + frame / fps), W, H) : undefined;
  return (
    <div style={{ position: "absolute", inset: 0, WebkitMaskImage: mask, maskImage: mask, maskSize: "100% 100%" }}>
      <div
        style={{
          ...box(r),
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: DISPLAY,
          fontSize: r.fontSize,
          lineHeight: 1,
          color: o.color ?? accent,
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          letterSpacing: "0.01em",
          opacity: env,
          translate: `0 ${mix(60 * u, 0, t) + mix(0, -30 * u, out)}px`,
          scale: String(mix(0.92, 1, t)),
          textShadow: "0 10px 40px rgba(0,0,0,0.35)",
        }}
      >
        {o.text}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- kinetic title

export const Title: React.FC<Base<KineticTitle>> = ({ o, r, accent, u }) => {
  const { len, env } = useWindow(o.start, o.end);
  const lines = wrap(o.text.toUpperCase(), r.fontSize, r.w, GLYPH.anton);
  return (
    <div style={{ ...box(r), opacity: env, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      {lines.map((line, i) => (
        <div key={i} style={{ fontFamily: DISPLAY, fontSize: r.fontSize, lineHeight: 1.08, color: "white", textAlign: "center", whiteSpace: "nowrap", textShadow: SHADOW }}>
          <WordStagger
            text={line}
            mode="mask"
            start={i * 4}
            stagger={3}
            duration={14}
            exitAt={len - 10}
            exitDuration={8}
            emphasis={(o.emphasis ?? []).map((e) => e.toUpperCase())}
            emphasisStyle={{ color: accent }}
          />
        </div>
      ))}
      <div style={{ height: 8 * u }} />
    </div>
  );
};

// ---------------------------------------------------------------- card

export const InfoCard: React.FC<Base<Card>> = ({ o, r, accent, u }) => {
  const { frame, len, env } = useWindow(o.start, o.end);
  const k = r.scale * u;
  const t = progress(frame, 0, 16, ease.overshootSoft);
  const out = progress(frame, len - 8, 8, ease.in);
  return (
    <div
      style={{
        ...box(r),
        ...GLASS,
        borderRadius: 28 * k,
        padding: `${32 * k}px ${36 * k}px`,
        boxSizing: "border-box",
        opacity: env,
        scale: String(mix(0.9, 1, t) * mix(1, 0.96, out)),
        translate: `0 ${mix(30 * u, 0, t)}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", left: 0, top: 24 * k, bottom: 24 * k, width: 8 * k, borderRadius: 4 * k, background: accent }} />
      {o.kicker ? (
        <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: 26 * k, letterSpacing: "0.12em", color: accent, textTransform: "uppercase", marginBottom: 18 * k }}>
          {o.kicker}
        </div>
      ) : null}
      <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: r.fontSize, lineHeight: 1.18, color: "white" }}>{o.title}</div>
      {o.body ? (
        <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: 32 * k, lineHeight: 1.3, color: "rgba(255,255,255,0.72)", marginTop: 14 * k }}>{o.body}</div>
      ) : null}
    </div>
  );
};

// ---------------------------------------------------------------- checklist

const Check: React.FC<{ done: number; spin: number; size: number; accent: string }> = ({ done, spin, size, accent }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" style={{ flexShrink: 0 }}>
    <circle cx="20" cy="20" r="17" fill={done > 0 ? accent : "none"} stroke={done > 0 ? accent : "rgba(255,255,255,0.35)"} strokeWidth="3" />
    {done <= 0 ? (
      <circle cx="20" cy="20" r="17" fill="none" stroke="white" strokeWidth="3" strokeDasharray="26 200" strokeLinecap="round" transform={`rotate(${spin} 20 20)`} />
    ) : (
      <path d="M11 20.5 L17.5 27 L29 14" fill="none" stroke="#111" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="30" strokeDashoffset={30 * (1 - done)} />
    )}
  </svg>
);

export const ChecklistCard: React.FC<Base<Checklist>> = ({ o, r, accent, u }) => {
  const { frame, fps, env } = useWindow(o.start, o.end);
  const k = r.scale * u;
  const t = progress(frame, 0, 14, ease.out);
  const doneCount = o.items.filter((it) => frame >= Math.round((it.at - o.start) * fps)).length;
  return (
    <div
      style={{
        ...box(r),
        ...GLASS,
        borderRadius: 30 * k,
        padding: `${32 * k}px ${36 * k}px`,
        boxSizing: "border-box",
        opacity: env,
        translate: `0 ${mix(40 * u, 0, t)}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {o.title ? (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", height: 72 * k }}>
          <span style={{ fontFamily: BODY, fontWeight: 800, fontSize: 34 * k, color: "white", textTransform: "uppercase", letterSpacing: "0.06em" }}>{o.title}</span>
          <span style={{ fontFamily: BODY, fontWeight: 800, fontSize: 28 * k, color: accent, fontVariantNumeric: "tabular-nums" }}>
            {doneCount}/{o.items.length}
          </span>
        </div>
      ) : null}
      {o.items.map((it, i) => {
        const appear = progress(frame, 4 + i * 4, 12, ease.out);
        const at = Math.round((it.at - o.start) * fps);
        const done = progress(frame, at, 8, ease.out);
        const pop = interpolate(frame - at, [0, 4, 10], [1, 1.06, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 26 * k,
              marginTop: 15 * k,
              marginBottom: 15 * k,
              opacity: appear * (frame >= at ? 1 : 0.55),
              translate: `${mix(-24 * u, 0, appear)}px 0`,
              scale: String(pop),
              transformOrigin: "left center",
            }}
          >
            <Check done={done} spin={(frame * 12) % 360} size={50 * k} accent={accent} />
            <span style={{ fontFamily: BODY, fontWeight: 800, fontSize: r.fontSize, lineHeight: 1.3, color: "white", textDecoration: "none" }}>{it.text}</span>
          </div>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------- lower third

export const LowerThirdBar: React.FC<Base<LowerThird>> = ({ o, r, accent, u }) => {
  const { frame, len, env } = useWindow(o.start, o.end);
  const k = r.scale * u;
  const t = progress(frame, 0, 16, ease.out);
  const out = progress(frame, len - 10, 10, ease.in);
  const reveal = mix(100, 0, t) + mix(0, 100, out); // % of the plate hidden (wipe from the left)
  return (
    <div style={{ ...box(r), opacity: Math.min(1, env * 1.5), clipPath: `inset(0 ${reveal}% 0 0)` }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 14 * k, background: accent, borderRadius: 4 * k }} />
      <div
        style={{
          position: "absolute",
          left: 26 * k,
          top: 0,
          bottom: 0,
          right: 0,
          background: "rgba(10,12,16,0.78)",
          borderRadius: 8 * k,
          padding: `0 ${30 * k}px`,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <div style={{ fontFamily: DISPLAY, fontSize: r.fontSize, lineHeight: 1.05, color: "white", textTransform: "uppercase", whiteSpace: "nowrap" }}>{o.name}</div>
        {o.role ? (
          <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: 30 * k, color: "rgba(255,255,255,0.75)", marginTop: 6 * k, whiteSpace: "nowrap" }}>{o.role}</div>
        ) : null}
      </div>
    </div>
  );
};
