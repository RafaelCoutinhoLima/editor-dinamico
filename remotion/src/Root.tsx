import React from "react";
import { Composition, type CalculateMetadataFunction } from "remotion";
import { EdinOverlay } from "./EdinOverlay";
import type { EdinProps } from "./types";
import "./fonts";

const defaults: EdinProps = {
  video: "edin/video.mp4",
  person: null,
  width: 1080,
  height: 1920,
  fps: 30,
  duration: 5,
  words: [],
  face: [],
  overlays: [],
  accent: "#FFE500",
  showGuides: false,
};

// Size, fps and length come from the props written by edin/remotion_bridge.py.
const calculateMetadata: CalculateMetadataFunction<EdinProps> = ({ props }) => ({
  width: props.width,
  height: props.height,
  fps: props.fps,
  durationInFrames: Math.max(1, Math.round(props.duration * props.fps)),
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EdinOverlay"
    component={EdinOverlay}
    defaultProps={defaults}
    calculateMetadata={calculateMetadata}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={150}
  />
);
