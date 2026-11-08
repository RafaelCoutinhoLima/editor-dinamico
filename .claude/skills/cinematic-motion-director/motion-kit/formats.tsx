import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";

/** Canvas sizes for social and ads. fps 30 unless the brief says otherwise. */
export const FORMATS = {
  vertical: { width: 1080, height: 1920, label: "9:16 Reels / TikTok / Shorts / Stories" },
  portrait: { width: 1080, height: 1350, label: "4:5 Feed" },
  square: { width: 1080, height: 1080, label: "1:1 Feed" },
  landscape: { width: 1920, height: 1080, label: "16:9 YouTube / Web" },
} as const;

export type FormatName = keyof typeof FORMATS;

/**
 * UI-free zones as fractions of the canvas (top, right, bottom, left).
 * Conservative values compiled from platform guides in 2026; platforms change
 * their overlays often — confirm with the Ads Manager safe-zone preview before launch.
 */
export const SAFE_ZONES = {
  "meta-reels": { top: 0.14, right: 0.06, bottom: 0.35, left: 0.06 },
  tiktok: { top: 0.09, right: 0.12, bottom: 0.3, left: 0.06 },
  "yt-shorts": { top: 0.1, right: 0.12, bottom: 0.25, left: 0.06 },
  feed: { top: 0.05, right: 0.05, bottom: 0.05, left: 0.05 },
} as const;

export type SafeZoneName = keyof typeof SAFE_ZONES;

/** Pixel insets for the current composition. Use them as padding for text/logo containers. */
export const useSafeArea = (zone: SafeZoneName) => {
  const { width, height } = useVideoConfig();
  const z = SAFE_ZONES[zone];
  return { top: z.top * height, right: z.right * width, bottom: z.bottom * height, left: z.left * width };
};

/**
 * SafeZoneGuide: red overlay of the areas covered by platform UI.
 * Review only — gate it behind a prop (e.g. showGuides) and never ship it.
 */
export const SafeZoneGuide: React.FC<{ zone: SafeZoneName }> = ({ zone }) => {
  const s = useSafeArea(zone);
  const band = "rgba(255,0,60,0.28)";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: s.top, background: band }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: s.bottom, background: band }} />
      <div style={{ position: "absolute", top: s.top, bottom: s.bottom, left: 0, width: s.left, background: band }} />
      <div style={{ position: "absolute", top: s.top, bottom: s.bottom, right: 0, width: s.right, background: band }} />
    </AbsoluteFill>
  );
};
