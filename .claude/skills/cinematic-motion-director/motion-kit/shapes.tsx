import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, type EasingFunction } from "remotion";
import { ease, mix, progress } from "./easing";

/**
 * DrawLine: any SVG path draws itself on (pathLength trick, no extra package).
 * Purpose: connectors, underlines, strike-throughs, diagrams, map routes.
 */
export const DrawLine: React.FC<{
  d: string;
  start?: number;
  duration?: number;
  easing?: EasingFunction;
  stroke: string;
  strokeWidth?: number;
  /** viewBox of the path coordinates. Defaults to the composition size. */
  viewBox?: string;
  style?: React.CSSProperties;
}> = ({ d, start = 0, duration = 20, easing = ease.inOut, stroke, strokeWidth = 4, viewBox, style }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const t = progress(frame, start, duration, easing);
  return (
    <svg
      viewBox={viewBox ?? `0 0 ${width} ${height}`}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible", ...style }}
    >
      <path
        d={d}
        pathLength={1}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray="1 1"
        strokeDashoffset={1 - t}
      />
    </svg>
  );
};

/**
 * GridReveal: editorial grid lines draw in with a stagger.
 * Purpose: establishes structure ("system", "method", "references") and gives
 * the eye alignment anchors. Keep opacity low (0.08–0.2); it is scaffolding.
 */
export const GridReveal: React.FC<{
  columns?: number;
  rows?: number;
  margin?: number;
  color: string;
  start?: number;
  stagger?: number;
  duration?: number;
  opacity?: number;
}> = ({ columns = 6, rows = 10, margin = 88, color, start = 0, stagger = 2, duration = 24, opacity = 0.14 }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const cols = Array.from({ length: columns + 1 }, (_, i) => margin + ((width - margin * 2) / columns) * i);
  const rws = Array.from({ length: rows + 1 }, (_, i) => margin + ((height - margin * 2) / rows) * i);
  return (
    <AbsoluteFill style={{ opacity }}>
      {cols.map((x, i) => (
        <div
          key={`c${i}`}
          style={{
            position: "absolute",
            left: x,
            top: 0,
            width: 1.5,
            height: "100%",
            background: color,
            transformOrigin: "top",
            scale: `1 ${progress(frame, start + i * stagger, duration, ease.inOut)}`,
          }}
        />
      ))}
      {rws.map((y, i) => (
        <div
          key={`r${i}`}
          style={{
            position: "absolute",
            top: y,
            left: 0,
            height: 1.5,
            width: "100%",
            background: color,
            transformOrigin: "left",
            scale: `${progress(frame, start + 6 + i * stagger, duration, ease.inOut)} 1`,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

/**
 * IrisReveal: children appear through a growing circle (or close with `reverse`).
 * Purpose: shape-driven match cut — end a scene on a dot, open the next from it.
 * cx/cy in % of the frame so the iris can start exactly on the previous focal point.
 */
export const IrisReveal: React.FC<{
  children: React.ReactNode;
  start?: number;
  duration?: number;
  cx?: number;
  cy?: number;
  reverse?: boolean;
  easing?: EasingFunction;
}> = ({ children, start = 0, duration = 24, cx = 50, cy = 50, reverse = false, easing = ease.inOut }) => {
  const frame = useCurrentFrame();
  const t = progress(frame, start, duration, easing);
  const r = mix(0, 150, reverse ? 1 - t : t);
  return <AbsoluteFill style={{ clipPath: `circle(${r}% at ${cx}% ${cy}%)` }}>{children}</AbsoluteFill>;
};

/**
 * CountUp: a number rolls to its value.
 * Purpose: proof points in ads (users, %, revenue). Hold the final value ≥ 1s.
 * Uses tabular figures so the width does not jitter.
 */
export const CountUp: React.FC<{
  to: number;
  from?: number;
  start?: number;
  duration?: number;
  decimals?: number;
  locale?: string;
  prefix?: string;
  suffix?: string;
  style?: React.CSSProperties;
}> = ({ to, from = 0, start = 0, duration = 36, decimals = 0, locale = "pt-BR", prefix = "", suffix = "", style }) => {
  const frame = useCurrentFrame();
  const value = mix(from, to, progress(frame, start, duration, ease.out));
  const text = value.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>
      {prefix}
      {text}
      {suffix}
    </span>
  );
};
