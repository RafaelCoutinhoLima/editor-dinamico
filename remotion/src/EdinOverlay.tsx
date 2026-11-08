// EdinOverlay: the video already cut by edin + motion overlays on top.
// Layers (back to front): edited video -> behind-head words -> person cutout (only while a
// behind-head word is on) -> cards / titles / checklists / lower thirds -> pill captions.
import React, { useMemo } from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useVideoConfig } from "remotion";
import { Captions } from "./Captions";
import { computeLayout, headUnion, type Placed } from "./layout";
import { BehindWord, ChecklistCard, InfoCard, LowerThirdBar, Title } from "./overlays";
import type { CaptionPill, EdinProps, Overlay } from "./types";

const Guides: React.FC<{ props: EdinProps; layout: ReturnType<typeof computeLayout> }> = ({ props, layout }) => {
  const { width: W, height: H } = props;
  const band = "rgba(255,0,60,0.25)";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: layout.safe.top, background: band }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: layout.safe.bottom, background: band }} />
      <div style={{ position: "absolute", left: layout.band.x, top: layout.band.y, width: layout.band.w, height: layout.band.h, outline: "3px dashed cyan" }} />
      {props.overlays.map((o, i) => {
        const r = layout.placed[i];
        if (!r) return null;
        const head = headUnion(props.face, o.start, o.end, W, H);
        return (
          <Sequence key={i} from={Math.round(o.start * props.fps)} durationInFrames={Math.max(1, Math.round((o.end - o.start) * props.fps))} layout="none">
            <div style={{ position: "absolute", left: head.x, top: head.y, width: head.w, height: head.h, outline: "3px solid lime" }} />
            <div style={{ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h, outline: "3px dashed yellow" }} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const EdinOverlay: React.FC<EdinProps> = (props) => {
  const { fps } = useVideoConfig();
  const layout = useMemo(() => computeLayout(props), [props]);
  const { overlays, accent } = props;
  const u = layout.unit;
  const masked = !props.person;
  const win = (o: Overlay) => ({
    from: Math.round(o.start * fps),
    durationInFrames: Math.max(1, Math.round((o.end - o.start) * fps)),
  });
  const behind = overlays.map((o, i) => [o, i] as const).filter(([o]) => o.type === "behind-head-word");
  const front = overlays.map((o, i) => [o, i] as const).filter(([o]) => o.type !== "behind-head-word" && o.type !== "caption-pill");
  const caps = overlays.filter((o): o is CaptionPill => o.type === "caption-pill");
  const hiders = overlays.filter((_, i) => layout.placed[i]?.hideCaptions);
  if (layout.warnings.length) console.warn("[EdinOverlay]", layout.warnings.join("; "));

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <OffthreadVideo src={staticFile(props.video)} style={{ width: "100%", height: "100%" }} />

      {behind.map(([o, i]) => (
        <Sequence key={`b${i}`} {...win(o)} premountFor={fps} name={`behind: ${(o as { text: string }).text}`}>
          <BehindWord o={o as never} r={layout.placed[i] as Placed} accent={accent} u={u} face={props.face} masked={masked} />
          {props.person ? (
            <OffthreadVideo src={staticFile(props.person)} transparent muted trimBefore={win(o).from} style={{ position: "absolute", width: "100%", height: "100%" }} />
          ) : null}
        </Sequence>
      ))}

      {front.map(([o, i]) => {
        const r = layout.placed[i];
        if (!r) return null; // skipped by the layout (see warnings)
        const common = { r, accent, u };
        return (
          <Sequence key={`f${i}`} {...win(o)} premountFor={fps} name={o.type}>
            {o.type === "kinetic-title" ? <Title o={o} {...common} /> : null}
            {o.type === "card" ? <InfoCard o={o} {...common} /> : null}
            {o.type === "checklist" ? <ChecklistCard o={o} {...common} /> : null}
            {o.type === "lower-third" ? <LowerThirdBar o={o} {...common} /> : null}
          </Sequence>
        );
      })}

      {caps.length ? (
        <Captions
          words={props.words}
          cfg={caps}
          band={layout.band}
          accent={accent}
          u={u}
          hidden={(t) => hiders.some((o) => t >= o.start - 0.1 && t < o.end + 0.1)}
        />
      ) : null}

      {props.showGuides ? <Guides props={props} layout={layout} /> : null}
    </AbsoluteFill>
  );
};
