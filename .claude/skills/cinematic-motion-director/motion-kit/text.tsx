import React from "react";
import { random, useCurrentFrame, useVideoConfig, type EasingFunction } from "remotion";
import { ease, mix, progress } from "./easing";

/**
 * Kinetic typography presets. All timing props are in FRAMES:
 *   <MaskReveal start={0.4 * fps} duration={0.6 * fps}>...</MaskReveal>
 * `exitAt` (optional) plays the reverse move with an accelerating curve.
 */
type Timing = {
  start?: number;
  duration?: number;
  easing?: EasingFunction;
  /** Frame where the element starts leaving. Omit to stay on screen. */
  exitAt?: number;
  exitDuration?: number;
};

const useInOut = ({ start = 0, duration = 18, easing = ease.out, exitAt, exitDuration = 12 }: Timing) => {
  const frame = useCurrentFrame();
  const enter = progress(frame, start, duration, easing);
  const exit = exitAt === undefined ? 0 : progress(frame, exitAt, exitDuration, ease.in);
  return { frame, enter, exit };
};

/**
 * MaskReveal: a line slides out from behind an invisible edge.
 * Purpose: the cleanest premium entrance for headlines. One line per instance.
 * Limits: the mask clips descenders if lineHeight < 1.1; keep paddingBottom.
 */
export const MaskReveal: React.FC<
  Timing & { children: React.ReactNode; from?: "below" | "above"; style?: React.CSSProperties }
> = ({ children, from = "below", style, ...timing }) => {
  const { enter, exit } = useInOut(timing);
  const dir = from === "below" ? 1 : -1;
  const y = mix(110 * dir, 0, enter) + mix(0, -110 * dir, exit);
  return (
    <span style={{ display: "block", overflow: "hidden", paddingBottom: "0.08em", ...style }}>
      <span style={{ display: "block", translate: `0 ${y}%` }}>{children}</span>
    </span>
  );
};

const clean = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

/**
 * WordStagger: words arrive one after another.
 * Purpose: mirrors speech rhythm; set `stagger` close to the narrator's word rate.
 * `emphasis` words get `emphasisStyle` (accent color, weight) — max 1–2 per line.
 * Modes: "rise" (fade + lift + optional blur) | "mask" (each word slides up from a clip).
 */
export const WordStagger: React.FC<
  Timing & {
    text: string;
    stagger?: number;
    mode?: "rise" | "mask";
    lift?: number;
    blur?: number;
    emphasis?: string[];
    emphasisStyle?: React.CSSProperties;
    style?: React.CSSProperties;
  }
> = ({
  text,
  stagger = 3,
  mode = "rise",
  lift = 40,
  blur = 8,
  emphasis = [],
  emphasisStyle,
  style,
  start = 0,
  duration = 16,
  easing = ease.out,
  exitAt,
  exitDuration = 10,
}) => {
  const frame = useCurrentFrame();
  const marks = new Set(emphasis.map(clean));
  const words = text.split(/\s+/).filter(Boolean);
  return (
    <span style={{ display: "inline", ...style }}>
      {words.map((word, i) => {
        const t = progress(frame, start + i * stagger, duration, easing);
        const out = exitAt === undefined ? 0 : progress(frame, exitAt + i * Math.ceil(stagger / 2), exitDuration, ease.in);
        const isMark = marks.has(clean(word));
        const wordStyle: React.CSSProperties = isMark ? (emphasisStyle ?? {}) : {};
        const gap = i < words.length - 1 ? " " : "";
        if (mode === "mask") {
          return (
            <React.Fragment key={i}>
              <span style={{ display: "inline-block", overflow: "hidden", verticalAlign: "top", paddingBottom: "0.08em" }}>
                <span style={{ display: "inline-block", translate: `0 ${mix(105, 0, t) + mix(0, -105, out)}%`, ...wordStyle }}>
                  {word}
                </span>
              </span>
              {gap}
            </React.Fragment>
          );
        }
        return (
          <React.Fragment key={i}>
            <span
              style={{
                display: "inline-block",
                opacity: t * (1 - out),
                translate: `0 ${mix(lift, 0, t) + mix(0, -lift / 2, out)}px`,
                filter: blur ? `blur(${mix(blur, 0, t) + mix(0, blur, out)}px)` : undefined,
                ...wordStyle,
              }}
            >
              {word}
            </span>
            {gap}
          </React.Fragment>
        );
      })}
    </span>
  );
};

/**
 * CharCascade: characters flip up on the X axis, one by one.
 * Purpose: short, monumental words (1–2 words). Too slow for sentences.
 */
export const CharCascade: React.FC<
  Timing & { text: string; stagger?: number; style?: React.CSSProperties; charStyle?: React.CSSProperties }
> = ({ text, stagger = 2, style, charStyle, start = 0, duration = 18, easing = ease.out, exitAt, exitDuration = 10 }) => {
  const frame = useCurrentFrame();
  return (
    <span style={{ display: "inline-block", perspective: 900, whiteSpace: "pre", ...style }}>
      {[...text].map((ch, i) => {
        const t = progress(frame, start + i * stagger, duration, easing);
        const out = exitAt === undefined ? 0 : progress(frame, exitAt + i, exitDuration, ease.in);
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transformOrigin: "50% 100%",
              rotate: `x ${mix(-95, 0, t) + mix(0, 95, out)}deg`,
              opacity: Math.min(1, t * 2) * (1 - out),
              ...charStyle,
            }}
          >
            {ch === " " ? " " : ch}
          </span>
        );
      })}
    </span>
  );
};

/**
 * TrackingIn: wide letter-spacing collapses into place while sharpening.
 * Purpose: a calm, cinematic title card. Pair with a slow camera push.
 */
export const TrackingIn: React.FC<
  Timing & { children: React.ReactNode; fromEm?: number; toEm?: number; blur?: number; style?: React.CSSProperties }
> = ({ children, fromEm = 0.6, toEm = -0.03, blur = 12, style, ...timing }) => {
  const { enter, exit } = useInOut({ duration: 30, ...timing });
  return (
    <span
      style={{
        display: "inline-block",
        whiteSpace: "nowrap",
        letterSpacing: `${mix(fromEm, toEm, enter)}em`,
        opacity: enter * (1 - exit),
        filter: `blur(${mix(blur, 0, enter) + mix(0, blur, exit)}px)`,
        ...style,
      }}
    >
      {children}
    </span>
  );
};

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>/{}[]=+*#_";

/**
 * Scramble: characters decode from noise into the final text.
 * Purpose: "code", "data", "AI", "system" beats. Deterministic: same frame → same glyphs.
 * Limits: use a monospaced font or the line width will jitter.
 */
export const Scramble: React.FC<{
  text: string;
  start?: number;
  /** Frames between each character locking in. */
  stagger?: number;
  /** How many frames each glyph flickers before locking. */
  flicker?: number;
  seed?: string;
  charset?: string;
  style?: React.CSSProperties;
  lockedStyle?: React.CSSProperties;
}> = ({ text, start = 0, stagger = 1.5, flicker = 10, seed = "scramble", charset = GLYPHS, style, lockedStyle }) => {
  const frame = useCurrentFrame();
  return (
    <span style={{ whiteSpace: "pre", ...style }}>
      {[...text].map((ch, i) => {
        const lockAt = start + flicker + i * stagger;
        if (ch === " ") return " ";
        if (frame < start + i * stagger * 0.5) return <span key={i} style={{ opacity: 0 }}>{ch}</span>;
        if (frame >= lockAt) return <span key={i} style={lockedStyle}>{ch}</span>;
        // Change glyph every 2 frames, seeded so renders are reproducible.
        const r = random(`${seed}-${i}-${Math.floor(frame / 2)}`);
        return (
          <span key={i} style={{ opacity: 0.55 }}>
            {charset[Math.floor(r * charset.length)]}
          </span>
        );
      })}
    </span>
  );
};

/**
 * Highlight: a marker bar sweeps behind the text, left to right.
 * Purpose: point at the ONE word the viewer must remember (offer, keyword, CTA).
 * Wraps across lines correctly (box-decoration-break: clone).
 */
export const Highlight: React.FC<
  Timing & { children: React.ReactNode; color: string; height?: string; style?: React.CSSProperties }
> = ({ children, color, height = "0.42em", style, ...timing }) => {
  const { enter, exit } = useInOut(timing);
  const p = enter * (1 - exit);
  return (
    <span
      style={{
        backgroundImage: `linear-gradient(${color}, ${color})`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "0 88%",
        backgroundSize: `${p * 100}% ${height}`,
        boxDecorationBreak: "clone",
        WebkitBoxDecorationBreak: "clone",
        padding: "0 0.08em",
        ...style,
      }}
    >
      {children}
    </span>
  );
};

/**
 * Typewriter: characters appear at a keystroke rhythm; the caret blinks only when idle.
 * Purpose: prompts, search fields, command palettes, code. Not for headlines.
 * `cps` = characters per second (human typing ≈ 12–18). `jitter` varies keystroke timing,
 * seeded so it is deterministic.
 */
export const Typewriter: React.FC<{
  text: string;
  start?: number;
  cps?: number;
  jitter?: number;
  seed?: string;
  caret?: string;
  caretColor?: string;
  style?: React.CSSProperties;
}> = ({ text, start = 0, cps = 15, jitter = 0.35, seed = "type", caret = "▍", caretColor, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Keystroke times with seeded human jitter.
  let t = start;
  let shown = 0;
  let lastKey = start;
  for (let i = 0; i < text.length; i++) {
    t += (fps / cps) * (1 + (random(`${seed}-${i}`) - 0.5) * 2 * jitter);
    if (frame >= t) (shown = i + 1), (lastKey = t);
  }
  const idle = frame - lastKey > fps * 0.25 || shown === 0;
  const blinkOn = !idle || Math.floor((frame - lastKey) / (fps * 0.5)) % 2 === 0;
  return (
    <span style={{ whiteSpace: "pre-wrap", ...style }}>
      {text.slice(0, shown)}
      <span style={{ opacity: blinkOn ? 1 : 0, color: caretColor }}>{caret}</span>
    </span>
  );
};
