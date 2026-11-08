import React from "react";
import { AbsoluteFill, OffthreadVideo, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// "Behind the head" depth for talking-head footage. Inputs come from scripts/person-matte.py:
// person.webm (the speaker on transparent pixels) and face.json (smoothed face track).
// Stack: base video -> `behind` layers -> person cutout -> `front` layers. Both videos must
// start on the same source time (pass the same startFrom to both).

export type FaceTrack = { fps: number; width: number; height: number; start: number; frames: [number, number, number][] };
export type Face = { cx: number; cy: number; w: number };

/** Face centre and width (px, composition space) at the current frame; `offset` = frames into the clip. */
export const useFace = (track: FaceTrack, offset = 0): Face => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const k = width / track.width;
  const i = Math.min(track.frames.length - 1, Math.max(0, Math.round(((frame + offset) / fps) * track.fps)));
  const [cx, cy, w] = track.frames[i];
  return { cx: cx * k, cy: cy * k, w: w * k };
};

/** True when a box (px) would cover the face: use it in the spacing pass and to move cards. */
export const coversFace = (f: Face, box: { x: number; y: number; w: number; h: number }, pad = 0.15) => {
  const fx0 = f.cx - f.w * (0.5 + pad), fx1 = f.cx + f.w * (0.5 + pad);
  const fy0 = f.cy - f.w * (0.75 + pad), fy1 = f.cy + f.w * (0.75 + pad);
  return box.x < fx1 && box.x + box.w > fx0 && box.y < fy1 && box.y + box.h > fy0;
};

/** Keep a box inside the frame with a side margin (px): anchored cards must never leave the safe area. */
export const keepInside = (x: number, w: number, W: number, margin = 60) => Math.max(margin, Math.min(W - margin - w, x));

const zoomParams = (f: Face, zoom: number, W: number, H: number, headAt: number) => {
  const z = Math.min(2, Math.max(1, zoom));
  const tx = Math.max(-(W * (z - 1)) / 2, Math.min((W * (z - 1)) / 2, (W / 2 - f.cx) * z));
  const ty = Math.max(-(H * (z - 1)) / 2, Math.min((H * (z - 1)) / 2, (H * headAt - f.cy) * z + (H / 2 - H * headAt) * (z - 1)));
  return { z, tx, ty };
};

/** Camera push toward the face, capped at 2x (footage stays sharp); keeps the head at `headAt` of the height. */
export const faceZoom = (f: Face, zoom: number, W: number, H: number, headAt = 0.4): React.CSSProperties => {
  const { z, tx, ty } = zoomParams(f, zoom, W, H, headAt);
  return { transform: `translate(${tx}px, ${ty}px) scale(${z})`, transformOrigin: "50% 50%" };
};

/** Where the face lands on screen after faceZoom (same arguments): anchor `front` cards on this. */
export const faceOnScreen = (f: Face, zoom: number, W: number, H: number, headAt = 0.4): Face => {
  const { z, tx, ty } = zoomParams(f, zoom, W, H, headAt);
  return { cx: W / 2 + tx + (f.cx - W / 2) * z, cy: H / 2 + ty + (f.cy - H / 2) * z, w: f.w * z };
};

/** First spot beside the face (right, left, above, below) that stays inside the frame and off the face. */
export const placeBeside = (f: Face, w: number, h: number, W: number, H: number, margin = 60, gap = 0.2) => {
  const r = f.w * (0.5 + gap), v = f.w * (0.8 + gap);
  const spots = [
    { x: f.cx + r, y: f.cy - h / 2 }, { x: f.cx - r - w, y: f.cy - h / 2 },
    { x: f.cx - w / 2, y: f.cy - v - h }, { x: f.cx - w / 2, y: f.cy + v },
  ];
  for (const p of spots) {
    const inside = p.x >= margin && p.x + w <= W - margin && p.y >= margin && p.y + h <= H - margin;
    if (inside && !coversFace(f, { ...p, w, h })) return p;
  }
  const p = spots[3];
  return { x: keepInside(p.x, w, W, margin), y: Math.min(H - margin - h, p.y) };
};

export const DepthStack: React.FC<{
  base: string;            // the original clip (with audio, or muted if the voice comes from elsewhere)
  person: string;          // person.webm from person-matte.py
  startFrom?: number;      // frames into both files
  muted?: boolean;
  camera?: React.CSSProperties; // e.g. faceZoom(...) — applied to base, behind and person together
  behind?: React.ReactNode;   // under the person, moves with the camera (face coordinates hold)
  anchored?: React.ReactNode; // over the person, moves with the camera: chips, brackets tied to the face
  front?: React.ReactNode;    // screen space, ignores the camera: captions, counters, headers
}> = ({ base, person, startFrom = 0, muted, camera, behind, anchored, front }) => (
  <AbsoluteFill>
    <AbsoluteFill style={camera}>
      <OffthreadVideo src={base} startFrom={startFrom} muted={muted} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill>{behind}</AbsoluteFill>
      <OffthreadVideo src={person} startFrom={startFrom} muted transparent style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill>{anchored}</AbsoluteFill>
    </AbsoluteFill>
    <AbsoluteFill>{front}</AbsoluteFill>
  </AbsoluteFill>
);

/** 0 -> 1 -> 0 envelope for an effect window (frames), with quick in/out — effects read best at 1.5–4 s. */
export const fxWindow = (frame: number, from: number, to: number, inF = 8, outF = 6) =>
  interpolate(frame, [from, from + inF, to - outF, to], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
