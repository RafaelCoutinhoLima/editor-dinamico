import React from "react";
import { AbsoluteFill, useCurrentFrame, type EasingFunction } from "remotion";
import { ease, mix, progress, tween } from "./easing";

/**
 * Cursor: a pointer that travels between waypoints and clicks.
 * Purpose: product demos where "a real click causes the next state" — the viewer reads
 * cause → effect. Place the click 2–4 frames BEFORE the state change it triggers.
 * Waypoints: { x, y } in px, `at` = frame when the cursor ARRIVES, `click` = press there.
 */
export type CursorStep = {
  x: number;
  y: number;
  at: number;
  click?: boolean;
  /** Frames to travel INTO this waypoint (overrides the component's `travel`). */
  travel?: number;
};

export const Cursor: React.FC<{
  path: readonly CursorStep[];
  /** Frames spent travelling to each waypoint. */
  travel?: number;
  size?: number;
  color?: string;
  ring?: string;
  easing?: EasingFunction;
}> = ({ path, travel = 18, size = 44, color = "#111", ring = "rgba(0,0,0,0.25)", easing = ease.inOut }) => {
  const frame = useCurrentFrame();
  let x = path[0]?.x ?? 0;
  let y = path[0]?.y ?? 0;
  for (let i = 1; i < path.length; i++) {
    const tr = path[i].travel ?? travel;
    const t = progress(frame, path[i].at - tr, tr, easing);
    if (t <= 0) break;
    // Slight arc: real hands don't move in straight lines.
    const arc = Math.sin(t * Math.PI) * Math.min(60, Math.hypot(path[i].x - path[i - 1].x, path[i].y - path[i - 1].y) * 0.12);
    x = mix(path[i - 1].x, path[i].x, t);
    y = mix(path[i - 1].y, path[i].y, t) - arc;
  }
  const click = path.find((p) => p.click && frame >= p.at && frame < p.at + 18);
  const press = click ? 1 - Math.sin(Math.min(1, (frame - click.at) / 6) * Math.PI) * 0.18 : 1;
  const r = click ? progress(frame, click.at, 16, ease.out) : 0;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {click ? (
        <div
          style={{
            position: "absolute",
            left: click.x - 40,
            top: click.y - 40,
            width: 80,
            height: 80,
            borderRadius: 40,
            border: `3px solid ${ring}`,
            scale: String(mix(0.3, 1.4, r)),
            opacity: 1 - r,
          }}
        />
      ) : null}
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        style={{ position: "absolute", left: x - size * 0.18, top: y - size * 0.08, scale: String(press), transformOrigin: "18% 8%", filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.25))" }}
      >
        <path d="M4 2 L4 20 L9 15.5 L12.5 22 L15.5 20.6 L12.2 14.2 L19 14 Z" fill={color} stroke="#fff" strokeWidth={1.4} strokeLinejoin="round" />
      </svg>
    </AbsoluteFill>
  );
};

/**
 * MorphBox: ONE element that becomes every state — size, radius, color and position morph,
 * content swaps through a short blur. "One shape, never cut."
 * Lessons from review: keep one fill color (a white↔black lerp passes through a "disabled"
 * grey); the shape itself stays solid and sharp; content leaves in the first ~35% of the
 * morph and enters once the shape is ~80% there; blur ≤ 4 px (more reads as a dissolve, not a
 * morph); geometry settles with a ~2-frame overshoot; states that reuse the same content
 * object (hover, press) don't swap content at all.
 * A state with a negative `at` lets frame 0 start mid-morph (seamless loops).
 * Purpose: UI/product stories (button → loader → card → result) with total continuity.
 * Each state starts morphing at `at` and takes `duration` frames. Make the last state equal
 * the first and the video loops seamlessly.
 */
export type MorphState = {
  at: number;
  w: number;
  h: number;
  radius: number;
  bg: string;
  x?: number;
  y?: number;
  content?: React.ReactNode;
};

const lerpColor = (a: string, b: string, t: number) => {
  const p = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return `rgb(${x.map((v, i) => Math.round(mix(v, y[i], t))).join(",")})`;
};

export const MorphBox: React.FC<{
  states: readonly MorphState[];
  duration?: number;
  easing?: EasingFunction;
  /** Old content is gone by this fraction of the morph DURATION (linear time, ~4 frames). */
  contentOut?: number;
  /** New content starts appearing at this fraction of the duration (shape mostly arrived). */
  contentIn?: number;
  /** Max blur (px) on content while it swaps. Keep it small: big blur reads as a dissolve. */
  blur?: number;
  style?: React.CSSProperties;
}> = ({ states, duration = 10, easing = ease.overshootSoft, contentOut = 0.4, contentIn = 0.6, blur = 4, style }) => {
  const frame = useCurrentFrame();
  let i = 0;
  while (i + 1 < states.length && frame >= states[i + 1].at) i++;
  const from = states[Math.max(0, i - 1)];
  const to = states[i];
  const t = i === 0 ? 1 : tween(frame, [to.at, to.at + duration], [0, 1], easing);
  const v = (k: "w" | "h" | "radius") => mix(from[k], to[k], t);
  const px = mix(from.x ?? 0, to.x ?? 0, t);
  const py = mix(from.y ?? 0, to.y ?? 0, t);
  // The SHAPE never blurs or fades — only its content swaps: quick exit, late entrance,
  // never both visible (keep the fill one color across states, or mid-morph tints read as "disabled").
  // Same content object (e.g. a hover state) → no swap at all, only the shape moves.
  const same = from.content === to.content;
  // Content timing runs on LINEAR time, not the eased shape progress: with an overshooting
  // ease the shape covers 30% in ~1 frame, which would delete the old content in one frame.
  const u = i === 0 ? 1 : Math.min(1, Math.max(0, (frame - to.at) / duration));
  const showNew = i === 0 || same || u >= contentIn;
  const c = i === 0 || same ? 1 : showNew ? Math.min(1, (u - contentIn) / (1 - contentIn)) : Math.max(0, 1 - u / contentOut);
  // Outgoing content shrinks as it leaves; incoming grows into place.
  const contentScale = showNew ? mix(0.97, 1, c) : mix(0.92, 1, c);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", pointerEvents: "none" }}>
      <div
        style={{
          width: v("w"),
          height: v("h"),
          borderRadius: v("radius"),
          background: /^#[0-9a-f]{6}$/i.test(from.bg) && /^#[0-9a-f]{6}$/i.test(to.bg) ? lerpColor(from.bg, to.bg, t) : to.bg,
          translate: `${px}px ${py}px`,
          overflow: "hidden",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          ...style,
        }}
      >
        <div style={{ opacity: c, filter: c < 1 && blur ? `blur(${(1 - c) * blur}px)` : undefined, scale: String(contentScale) }}>
          {showNew ? to.content : from.content}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Handoff: shared-element transition for an accent (a dot, an icon, a disc) that must never
 * disappear between states. During each hop ONE carrier travels from the element just used
 * to the accent of the next state; it draws the source `node` at its start and the target
 * `node` at its end, so the static elements can hide/appear on the hand-off frames with no pop.
 * Hide the source from `at - 3`, show the target from `at - 3 + dur`.
 * Derive target positions from the same function that draws them (pixel-exact landings),
 * or measure them from a rendered still — never eyeball.
 */
export type HandoffSpot = {
  x: number;
  y: number;
  /** Diameter of the carrier dot at this end. */
  d: number;
  /** Glyph drawn at this end (▶, ✦, an icon). Omit for a plain dot. */
  node?: React.ReactNode;
  /** true when the node sits ON the dot (e.g. an arrow on a circle) instead of replacing it. */
  onDot?: boolean;
  /** Rotate the node 45° while it enters/leaves (stars, plus signs). */
  spin?: boolean;
};
export type HandoffHop = { at: number; from: HandoffSpot; to: HandoffSpot; dur?: number };

export const Handoff: React.FC<{ hops: readonly HandoffHop[]; color: string; arc?: number }> = ({ hops, color, arc = 40 }) => {
  const frame = useCurrentFrame();
  const hop = hops.find((h) => frame >= h.at - 3 && frame < h.at - 3 + (h.dur ?? 13));
  if (!hop) return null;
  const dur = hop.dur ?? 13;
  const start = hop.at - 3;
  const t = progress(frame, start, dur, ease.inOut);
  const x = mix(hop.from.x, hop.to.x, t);
  const y = mix(hop.from.y, hop.to.y, t) - Math.sin(t * Math.PI) * Math.min(arc, Math.hypot(hop.to.x - hop.from.x, hop.to.y - hop.from.y) * 0.15);
  const d = mix(hop.from.d, hop.to.d, t);
  // Source glyph shrinks away over 4 frames while the dot grows in UNDER it at full opacity
  // (never two half-transparent shapes = no mud).
  // The target glyph only grows once the carrier has (almost) arrived — never before.
  const out = 1 - progress(frame, start, 4, ease.inOut);
  const inStart = start + Math.max(dur - 5, Math.round(dur * 0.7));
  const inn = progress(frame, inStart, start + dur - inStart, ease.overshootSoft);
  const dotK = (s: HandoffSpot, k: number) => (!s.node || s.onDot ? 1 : 1 - k);
  const dot = Math.min(dotK(hop.from, out), dotK(hop.to, inn));
  const mark = (s: HandoffSpot, k: number, rot: number) =>
    s.node && k > 0 ? (
      <div style={{ position: "absolute", left: s.x, top: s.y, translate: "-50% -50%", opacity: Math.min(1, k * 1.5), scale: String(mix(0.4, 1, k)), rotate: s.spin ? `${rot}deg` : undefined }}>{s.node}</div>
    ) : null;
  return (
    <>
      <div style={{ position: "absolute", left: x - d / 2, top: y - d / 2, width: d, height: d, borderRadius: d / 2, background: color, scale: String(mix(0.4, 1, dot)), opacity: dot > 0.02 ? 1 : 0 }} />
      {mark(hop.from, out, mix(0, 45, 1 - out))}
      {mark(hop.to, inn, mix(-45, 0, inn))}
    </>
  );
};
