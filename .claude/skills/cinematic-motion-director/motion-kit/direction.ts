import { ease, type EaseName } from "./easing";

/**
 * The art direction of ONE video, as data. Write a new one per project
 * (see templates/art-direction.md); scenes read from it instead of hard-coding
 * colors, sizes or timings, so a whole video can be re-directed in one place.
 */
export type Direction = {
  name: string;
  palette: {
    bg: string;
    surface: string;
    ink: string;
    muted: string;
    accent: string;
    /** Optional second accent. Two accents is the ceiling, not the target. */
    accent2?: string;
  };
  type: {
    display: string;
    text: string;
    mono: string;
    /** Font sizes in px for a 1080-wide canvas: [display, h1, h2, body, caption]. */
    scale: readonly [number, number, number, number, number];
    /** Tight negative tracking for display sizes, in em. */
    displayTracking: number;
  };
  layout: {
    /** Outer margin in px (1080-wide canvas). */
    margin: number;
    columns: number;
    gutter: number;
  };
  motion: {
    /** Durations in seconds. Multiply by fps at the call site. */
    fast: number;
    base: number;
    slow: number;
    /** Delay between staggered siblings, in seconds. */
    stagger: number;
    enter: EaseName;
    exit: EaseName;
    camera: EaseName;
  };
};

/**
 * Starting point for tech/creator content: dark, editorial, one hot accent.
 * Never ship it unchanged for a brand that has its own identity.
 */
export const signalNoir: Direction = {
  name: "Signal Noir",
  palette: {
    bg: "#0A0A0B",
    surface: "#141416",
    ink: "#F4F1EA",
    muted: "#8A8780",
    accent: "#FF4D1C",
    accent2: "#C8FF3D",
  },
  type: {
    display: "Inter Tight, Inter, system-ui, sans-serif",
    text: "Inter, system-ui, sans-serif",
    mono: "JetBrains Mono, ui-monospace, monospace",
    scale: [220, 120, 72, 44, 30],
    displayTracking: -0.045,
  },
  layout: { margin: 88, columns: 6, gutter: 24 },
  motion: {
    fast: 0.35,
    base: 0.6,
    slow: 1.1,
    stagger: 0.06,
    enter: "out",
    exit: "in",
    camera: "inOut",
  },
};

export const easeOf = (name: EaseName) => ease[name];
