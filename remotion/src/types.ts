// Props contract between edin (Python, edin/remotion_bridge.py) and the EdinOverlay composition.
// All times are SECONDS on the timeline of the video already cut by edin (output time).

export type Word = { i: number; w: string; s: number; e: number; blk?: number };

/** Face sample from edin's face_track on the edited video: centre (x, y) and face height, normalised 0..1. */
export type FaceSample = { t: number; x: number; y: number; size: number };

type Window = { start: number; end: number };

export type BehindHeadWord = Window & { type: "behind-head-word"; text: string; color?: string; size?: number };
export type KineticTitle = Window & { type: "kinetic-title"; text: string; emphasis?: string[] };
export type Card = Window & { type: "card"; title: string; body?: string; kicker?: string };
export type Checklist = Window & { type: "checklist"; title?: string; items: { text: string; at: number }[] };
export type LowerThird = Window & { type: "lower-third"; name: string; role?: string };
export type CaptionPill = Window & {
  type: "caption-pill";
  wordsPerPage?: number;
  uppercase?: boolean;
  emphasis?: number[]; // word indices (#n from `edin text`)
};

export type Overlay = BehindHeadWord | KineticTitle | Card | Checklist | LowerThird | CaptionPill;

export type EdinProps = {
  video: string; // path inside public/ (staticFile)
  person?: string | null; // person cutout (webm with alpha), same timing as `video`
  width: number;
  height: number;
  fps: number;
  duration: number; // seconds
  words: Word[];
  face: FaceSample[];
  overlays: Overlay[];
  accent: string;
  showGuides?: boolean;
};
