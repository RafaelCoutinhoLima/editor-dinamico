import React from "react";
import { AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { ease, mix, progress, tween } from "./easing";
import { MaskReveal, WordStagger } from "./text";
import { CountUp } from "./shapes";

/**
 * Voiceover-driven edit: an EDIT PLAN (JSON the agent writes) + the VOICE MAP from
 * scripts/voice-map.mjs → a finished timeline with narration slices, B-roll, sound bites
 * (original audio), motion scenes, captions and source credits.
 *
 * Not exported from ./index (it needs @remotion/media). Import it directly:
 *   import { EditTimeline, planTimeline } from "./motion/edit";
 *
 * Timeline rule: segments play in the listed order. A "vo" segment plays [from, to) of the
 * voiceover; a "bite" segment pauses the narration and plays a clip WITH its own audio.
 * Total duration = sum of segment durations (use planTimeline() in calculateMetadata).
 */

export type Word = { text: string; start: number; end: number };
export type VoiceMap = { audio: string; duration: number; words: Word[]; phrases: { text: string; start: number; end: number }[] };

export type Visual =
  | { type: "title"; text: string; kicker?: string; emphasis?: string[] }
  | { type: "kinetic"; text?: string; emphasis?: string[] } // defaults to the narration words of the slice
  | {
      type: "broll";
      src: string;
      from?: number;
      /** cover = crop to fill (set `focus` to keep the subject); contain-blur = whole frame over a blurred copy. */
      fit?: "cover" | "contain-blur";
      /** Crop focus for cover, in % [x, y] — e.g. [80, 50] keeps the right side of a 16:9 shot in 9:16. */
      focus?: [number, number];
      volume?: number;
      push?: number;
      credit?: string;
    }
  | { type: "image"; src: string; push?: number; credit?: string }
  | { type: "number"; value: number; prefix?: string; suffix?: string; label: string; decimals?: number }
  | { type: "scene"; name: string; props?: Record<string, unknown> }; // your own component, see `scenes`

export type Segment =
  | { kind: "vo"; from: number; to: number; visual: Visual }
  | {
      kind: "bite";
      src: string;
      from?: number; // seconds into `src` (0 for a pre-cut clip)
      to: number; // seconds into `src`
      credit?: string;
      fit?: "cover" | "contain-blur";
      volume?: number;
      transcript?: string; // public path of footage.mjs transcript.json → captions (loaded by resolveEditAssets)
      words?: Word[]; // transcript words in SOURCE time (filled by resolveEditAssets)
    };

export type EditPlan = {
  voice: { src: string; map: string; volume?: number }; // map = voice-map.mjs output (public path)
  segments: Segment[];
  music?: { src: string; volume?: number; duckedVolume?: number };
  /** on: "footage" (default) = only over B-roll/bites — type scenes already show the words. */
  captions?: { style?: "pill" | "plain" | "none"; y?: number; maxWords?: number; on?: "footage" | "all" };
  transition?: "cut" | "fade";
  /** Slow constant push on type scenes (title / kinetic / number / scene) so holds never go dead. 0 = off. */
  drift?: number;
  palette?: { bg: string; ink: string; accent: string; muted: string };
  fonts?: { display: string; text: string; mono: string };
};

export type PlacedSegment = { seg: Segment; start: number; duration: number };

/** Place segments on the output timeline. Use it in calculateMetadata for the duration. */
export const planTimeline = (plan: EditPlan) => {
  let t = 0;
  const placed: PlacedSegment[] = plan.segments.map((seg) => {
    const duration = Math.max(0.1, seg.to - (seg.kind === "vo" ? seg.from : seg.from ?? 0));
    const p = { seg, start: t, duration };
    t += duration;
    return p;
  });
  return { placed, duration: t };
};

/**
 * Load everything the edit needs at metadata time (Remotion's calculateMetadata may be async):
 *   calculateMetadata: async ({ props }) => {
 *     const { plan, voice } = await resolveEditAssets(props.plan);
 *     return { durationInFrames: Math.ceil(planTimeline(plan).duration * 30), props: { ...props, plan, voice } };
 *   }
 */
export const resolveEditAssets = async (plan: EditPlan): Promise<{ plan: EditPlan; voice: VoiceMap }> => {
  const load = async (p: string) => (await fetch(src(p))).json();
  const voice: VoiceMap = await load(plan.voice.map);
  const segments = await Promise.all(plan.segments.map(async (seg) => (seg.kind === "bite" && seg.transcript && !seg.words ? { ...seg, words: (await load(seg.transcript)).words as Word[] } : seg)));
  return { plan: { ...plan, segments }, voice };
};

const isFootage = (seg: Segment) => seg.kind === "bite" || seg.visual.type === "broll" || seg.visual.type === "image";

/** Words on the OUTPUT timeline (narration words shifted per vo slice + bite words). */
export const timelineWords = (plan: EditPlan, voice: VoiceMap, only?: "footage"): Word[] =>
  planTimeline(plan).placed.flatMap(({ seg, start }) => {
    if (only === "footage" && !isFootage(seg)) return [];
    if (seg.kind === "vo")
      return voice.words.filter((w) => w.start >= seg.from - 0.02 && w.start < seg.to).map((w) => ({ text: w.text, start: start + w.start - seg.from, end: start + Math.min(w.end, seg.to) - seg.from }));
    const off = seg.from ?? 0;
    return (seg.words ?? []).filter((w) => w.start >= off - 0.02 && w.start < seg.to).map((w) => ({ text: w.text, start: start + w.start - off, end: start + Math.min(w.end, seg.to) - off }));
  });

const DEFAULT_PALETTE = { bg: "#0A0A0B", ink: "#F4F1EA", accent: "#FF4D1C", muted: "#8A8780" };
const DEFAULT_FONTS = { display: "Inter Tight, Inter, sans-serif", text: "Inter, sans-serif", mono: "ui-monospace, monospace" };
const src = (s: string) => (/^https?:/.test(s) ? s : staticFile(s));

/** Footage that fills a frame of any aspect: crop to cover, or contain over a blurred copy. */
const Footage: React.FC<{ src: string; trimBefore: number; trimAfter: number; fit: "cover" | "contain-blur"; focus?: [number, number]; volume: number; push: number; frames: number }> = ({ src: s, trimBefore, trimAfter, fit, focus, volume, push, frames }) => {
  const frame = useCurrentFrame();
  const scale = String(1 + push * (frame / Math.max(1, frames))); // slow constant push: footage never sits dead
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {fit === "contain-blur" ? (
        <AbsoluteFill style={{ scale: "1.25", filter: "blur(36px) brightness(0.55)" }}>
          <Video src={src(s)} trimBefore={trimBefore} trimAfter={trimAfter} muted objectFit="cover" style={{ width: "100%", height: "100%" }} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{ scale }}>
        <Video src={src(s)} trimBefore={trimBefore} trimAfter={trimAfter} volume={volume} muted={volume === 0} objectFit={fit === "cover" ? "cover" : "contain"} style={{ width: "100%", height: "100%", objectPosition: focus ? `${focus[0]}% ${focus[1]}%` : undefined }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ImageView: React.FC<{ src: string; push: number; frames: number }> = ({ src: s, push, frames }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img src={src(s)} style={{ width: "100%", height: "100%", objectFit: "cover", scale: String(1 + push * (frame / frames)) }} />
    </AbsoluteFill>
  );
};

const CreditTag: React.FC<{ text: string; mono: string }> = ({ text, mono }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const t = progress(frame, 4, 10, ease.out);
  return (
    <div style={{ position: "absolute", left: width * 0.07, top: height * (height > width ? 0.15 : 0.06), padding: "10px 18px", borderRadius: 999, background: "rgba(0,0,0,0.55)", color: "#fff", fontFamily: mono, fontSize: Math.round(width / 40), opacity: t, translate: `0 ${mix(-12, 0, t)}px` }}>
      Fonte: {text}
    </div>
  );
};

const VisualView: React.FC<{ visual: Visual; seg: Segment & { kind: "vo" }; frames: number; words: Word[]; plan: EditPlan; scenes: Record<string, React.FC<any>> }> = ({ visual, seg, frames, words, plan, scenes }) => {
  const { fps, width } = useVideoConfig();
  const c = plan.palette ?? DEFAULT_PALETTE;
  const f = plan.fonts ?? DEFAULT_FONTS;
  const u = width / 1080;
  const pad = { padding: `0 ${88 * u}px`, justifyContent: "center" } as const;
  switch (visual.type) {
    case "broll":
      return <Footage src={visual.src} trimBefore={Math.round((visual.from ?? 0) * fps)} trimAfter={Math.round(((visual.from ?? 0) + (seg.to - seg.from)) * fps)} fit={visual.fit ?? "cover"} focus={visual.focus} volume={visual.volume ?? 0} push={visual.push ?? 0.06} frames={frames} />;
    case "image":
      return <ImageView src={visual.src} push={visual.push ?? 0.08} frames={frames} />;
    case "title":
      return (
        <AbsoluteFill style={{ ...pad, backgroundColor: c.bg, gap: 24 * u }}>
          {visual.kicker ? <div style={{ fontFamily: f.mono, fontSize: 30 * u, color: c.muted, textTransform: "uppercase", letterSpacing: "0.06em" }}><MaskReveal start={-6}>{visual.kicker}</MaskReveal></div> : null}
          <div style={{ fontFamily: f.display, fontWeight: 800, fontSize: 112 * u, lineHeight: 1.02, letterSpacing: "-0.045em", color: c.ink }}>
            <WordStagger text={visual.text} start={-5} stagger={3} mode="mask" emphasis={visual.emphasis} emphasisStyle={{ color: c.accent }} />
          </div>
        </AbsoluteFill>
      );
    case "kinetic": {
      // Words appear exactly when they are spoken (voice-map timings).
      const text = visual.text;
      return (
        <AbsoluteFill style={{ ...pad, backgroundColor: c.bg }}>
          <div style={{ fontFamily: f.display, fontWeight: 700, fontSize: 92 * u, lineHeight: 1.08, letterSpacing: "-0.035em", color: c.ink }}>
            {text ? (
              <WordStagger text={text} stagger={4} emphasis={visual.emphasis} emphasisStyle={{ color: c.accent }} />
            ) : (
              <SpokenWords words={words} emphasis={visual.emphasis ?? []} accent={c.accent} />
            )}
          </div>
        </AbsoluteFill>
      );
    }
    case "number":
      return (
        <AbsoluteFill style={{ ...pad, backgroundColor: c.bg, gap: 16 * u }}>
          <div style={{ fontFamily: f.display, fontWeight: 800, fontSize: 260 * u, letterSpacing: "-0.05em", color: c.accent, lineHeight: 1 }}>
            <CountUp to={visual.value} prefix={visual.prefix} suffix={visual.suffix} decimals={visual.decimals} start={-8} duration={Math.min(30, frames - 10)} />
          </div>
          <div style={{ fontFamily: f.text, fontSize: 48 * u, color: c.ink }}>
            <MaskReveal start={2}>{visual.label}</MaskReveal>
          </div>
        </AbsoluteFill>
      );
    case "scene": {
      const Scene = scenes[visual.name];
      if (!Scene) throw new Error(`EditTimeline: no scene component named "${visual.name}" in \`scenes\``);
      return <Scene {...(visual.props ?? {})} words={words} durationInFrames={frames} />;
    }
  }
};

/** Words of the current slice revealed on their spoken time (relative to the segment). */
const SpokenWords: React.FC<{ words: Word[]; emphasis: string[]; accent: string }> = ({ words, emphasis, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const marks = new Set(emphasis.map((e) => e.toLowerCase()));
  return (
    <span>
      {words.map((w, i) => {
        const k = tween(t, [w.start - 0.06, w.start + 0.12], [0, 1], ease.out);
        const isMark = marks.has(w.text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ""));
        return (
          <React.Fragment key={i}>
            <span style={{ display: "inline-block", opacity: k, translate: `0 ${mix(24, 0, k)}px`, color: isMark ? accent : undefined }}>{w.text}</span>{" "}
          </React.Fragment>
        );
      })}
    </span>
  );
};

/** TikTok-style captions from timeline words: pages of ≤ maxWords, active word highlighted. */
const Captions: React.FC<{ words: Word[]; style: "pill" | "plain"; y: number; maxWords: number; accent: string; font: string }> = ({ words, style, y, maxWords, accent, font }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  // Pages break on pauses ≥ 0.3 s or every maxWords words.
  const pages: Word[][] = [];
  words.forEach((w, i) => {
    const last = pages[pages.length - 1];
    if (!last || last.length >= maxWords || w.start - words[i - 1].end > 0.3) pages.push([w]);
    else last.push(w);
  });
  const page = pages.find((p) => t >= p[0].start - 0.05 && t < p[p.length - 1].end + 0.25);
  if (!page) return null;
  const pop = tween(t, [page[0].start - 0.05, page[0].start + 0.08], [0.85, 1], ease.out);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: height * y, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{ maxWidth: width * 0.84, textAlign: "center", padding: style === "pill" ? "14px 30px" : 0, borderRadius: 999, background: style === "pill" ? "rgba(0,0,0,0.62)" : "transparent", fontFamily: font, fontWeight: 800, fontSize: Math.round(width / 15), lineHeight: 1.1, textTransform: "uppercase", color: "#fff", scale: String(pop), textShadow: style === "plain" ? "0 4px 18px rgba(0,0,0,0.8)" : undefined }}>
        {page.map((w, i) => (
          <span key={i} style={{ color: t >= w.start && t < w.end + 0.08 ? accent : "#fff" }}>
            {w.text}
            {i < page.length - 1 ? " " : ""}
          </span>
        ))}
      </div>
    </div>
  );
};

export const EditTimeline: React.FC<{
  plan: EditPlan;
  voice: VoiceMap;
  /** Your own scene components for { type: "scene", name } visuals. They receive `words` and `durationInFrames`. */
  scenes?: Record<string, React.FC<any>>;
}> = ({ plan, voice, scenes = {} }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const c = plan.palette ?? DEFAULT_PALETTE;
  const f = plan.fonts ?? DEFAULT_FONTS;
  const { placed } = planTimeline(plan);
  const cap = plan.captions ?? {};
  const words = timelineWords(plan, voice, cap.on === "all" ? undefined : "footage");
  const inBite = placed.some(({ seg, start, duration }) => seg.kind === "bite" && frame >= start * fps && frame < (start + duration) * fps);
  return (
    <AbsoluteFill style={{ backgroundColor: c.bg }}>
      {plan.music ? <Audio src={src(plan.music.src)} volume={inBite ? plan.music.duckedVolume ?? 0.03 : plan.music.volume ?? 0.12} loop /> : null}
      {placed.map(({ seg, start, duration }, i) => {
        const from = Math.round(start * fps);
        const frames = Math.max(1, Math.round((start + duration) * fps) - from);
        const fade = plan.transition === "fade";
        return (
          <Sequence key={i} from={from} durationInFrames={frames} premountFor={fps}>
            <SegmentFade enabled={fade} frames={frames}>
              {seg.kind === "vo" ? (
                <>
                  <Audio src={src(plan.voice.src)} trimBefore={Math.round(seg.from * fps)} trimAfter={Math.round(seg.to * fps)} volume={plan.voice.volume ?? 1} />
                  <Drift amount={isFootage(seg) ? 0 : plan.drift ?? 0.04} frames={frames}>
                  <VisualView
                    visual={seg.visual}
                    seg={seg}
                    frames={frames}
                    words={voice.words.filter((w) => w.start >= seg.from - 0.02 && w.start < seg.to).map((w) => ({ ...w, start: w.start - seg.from, end: w.end - seg.from }))}
                    plan={plan}
                    scenes={scenes}
                  />
                  </Drift>
                  {seg.visual.type === "broll" || seg.visual.type === "image" ? (seg.visual.credit ? <CreditTag text={seg.visual.credit} mono={f.mono} /> : null) : null}
                </>
              ) : (
                <>
                  <Footage src={seg.src} trimBefore={Math.round((seg.from ?? 0) * fps)} trimAfter={Math.round(seg.to * fps)} fit={seg.fit ?? "contain-blur"} volume={seg.volume ?? 1} push={0.03} frames={frames} />
                  {seg.credit ? <CreditTag text={seg.credit} mono={f.mono} /> : null}
                </>
              )}
            </SegmentFade>
          </Sequence>
        );
      })}
      {cap.style !== "none" ? <Captions words={words} style={cap.style ?? "pill"} y={cap.y ?? 0.62} maxWords={cap.maxWords ?? 3} accent={c.accent} font={f.display} /> : null}
    </AbsoluteFill>
  );
};

const Drift: React.FC<{ amount: number; frames: number; children: React.ReactNode }> = ({ amount, frames, children }) => {
  const frame = useCurrentFrame();
  if (!amount) return <>{children}</>;
  return <AbsoluteFill style={{ scale: String(1 + amount * (frame / frames)) }}>{children}</AbsoluteFill>;
};

const SegmentFade: React.FC<{ enabled: boolean; frames: number; children: React.ReactNode }> = ({ enabled, frames, children }) => {
  const frame = useCurrentFrame();
  if (!enabled) return <AbsoluteFill>{children}</AbsoluteFill>;
  const o = Math.min(progress(frame, 0, 5, ease.out), 1 - progress(frame, frames - 4, 4, ease.in));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};
