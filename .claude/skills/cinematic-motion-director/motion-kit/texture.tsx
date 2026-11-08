import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

/**
 * Grain: deterministic film grain (SVG turbulence re-seeded every `every` frames).
 * Purpose: kills the sterile "rendered" look of flat digital gradients.
 * Keep opacity 0.04–0.10. If you can clearly see it on a phone, it is too strong.
 */
export const Grain: React.FC<{ opacity?: number; every?: number; scale?: number }> = ({
  opacity = 0.07,
  every = 2,
  scale = 0.9,
}) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / every);
  return (
    <AbsoluteFill style={{ opacity, mixBlendMode: "overlay", pointerEvents: "none" }}>
      <svg width="100%" height="100%">
        <filter id={`grain-${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency={scale} numOctaves={2} seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

/**
 * Vignette: darkens the edges to pull the eye to the center.
 * Purpose: focus and depth on dark directions. Skip it on bright, flat brand styles.
 */
export const Vignette: React.FC<{ strength?: number; color?: string }> = ({ strength = 0.55, color = "0,0,0" }) => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background: `radial-gradient(ellipse 75% 65% at 50% 45%, rgba(${color},0) 55%, rgba(${color},${strength}) 100%)`,
    }}
  />
);
