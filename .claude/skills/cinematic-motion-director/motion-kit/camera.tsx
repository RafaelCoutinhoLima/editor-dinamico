import React, { createContext, useContext } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

/**
 * 2.5D camera with parallax layers.
 *
 *   <Camera x={...} y={...} zoom={...} rotate={...} drift={4}>
 *     <Layer depth={0.2}>background</Layer>
 *     <Layer depth={1}>subject</Layer>
 *     <Layer depth={1.4}>foreground dust</Layer>
 *   </Camera>
 *
 * Camera values are plain numbers: drive them with tween() at the call site.
 * depth 0 = locked to screen, 1 = moves with the camera, >1 = closer than the subject.
 * For real geometry, lights or orbiting, use @remotion/three instead (see references).
 */
type CameraState = { x: number; y: number; zoom: number; rotate: number; dx: number; dy: number };

const CameraContext = createContext<CameraState>({ x: 0, y: 0, zoom: 1, rotate: 0, dx: 0, dy: 0 });
export const useCamera = () => useContext(CameraContext);

export const Camera: React.FC<{
  children: React.ReactNode;
  /** Camera position in px. Positive x moves the camera right (world moves left). */
  x?: number;
  y?: number;
  /** 1 = neutral. 1.15 = push-in. */
  zoom?: number;
  /** Roll in degrees. Keep under ~3° unless it is a stylistic beat. */
  rotate?: number;
  /** Handheld micro-drift amplitude in px. 0 = locked-off tripod. */
  drift?: number;
  style?: React.CSSProperties;
}> = ({ children, x = 0, y = 0, zoom = 1, rotate = 0, drift = 0, style }) => {
  const frame = useCurrentFrame();
  // Sum of incommensurate sines: smooth, deterministic, never loops visibly.
  const dx = drift * (Math.sin(frame / 37) * 0.6 + Math.sin(frame / 23 + 1.3) * 0.4);
  const dy = drift * (Math.sin(frame / 31 + 0.7) * 0.6 + Math.sin(frame / 19 + 2.1) * 0.4);
  return (
    <CameraContext.Provider value={{ x, y, zoom, rotate, dx, dy }}>
      <AbsoluteFill style={{ overflow: "hidden", ...style }}>{children}</AbsoluteFill>
    </CameraContext.Provider>
  );
};

export const Layer: React.FC<{ children: React.ReactNode; depth?: number; style?: React.CSSProperties }> = ({
  children,
  depth = 1,
  style,
}) => {
  const { x, y, zoom, rotate, dx, dy } = useCamera();
  return (
    <AbsoluteFill
      style={{
        translate: `${-(x + dx) * depth}px ${-(y + dy) * depth}px`,
        scale: String(1 + (zoom - 1) * depth),
        rotate: `${-rotate * Math.min(depth, 1)}deg`,
        ...style,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
