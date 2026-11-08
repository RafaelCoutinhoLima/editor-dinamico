# Character Animation (acting in code)

For short scenes where a character *acts*: a mascot, an illustrated brand card, a hand-drawn
figure.

## 1. The character is data

Build the character as one component with a typed rig, never as one-off drawings per scene:

```ts
type Rig = {
  view: "front" | "three-quarter" | "side" | "back";
  eyes: "open" | "closed" | "wide" | "squint" | "looking-left" | "looking-right";
  mouth: "neutral" | "smile" | "open" | "frown" | "o";
  brows: number;        // -1 angry … 0 … 1 surprised
  lean: number;         // degrees
  squash: number;       // 0.85 … 1.15 (squash & stretch, volume preserved)
  arms: { l: number; r: number }; // angles
};
const EMOTIONS: Record<string, Partial<Rig>> = { curious: {…}, frustrated: {…}, proud: {…} };
```

- Before any scene, render an **emotion sheet** (every emotion as a still, tiled) and get it
  approved. Characters drift off-model when each scene redraws them freehand.
- Emotions change through springs (`springSteps`), never by swapping frames.

## 2. Acting beats

A 10–15 s scene is a tiny story: **want → try → fail → try → fail → surprising success →
reaction**. Give each beat its own pose, hold each key pose ≥ 6 frames, add anticipation before
every action and overshoot + settle after it. Secondary action (blink, tail, antenna) runs
offset by 2–4 frames.

## 3. Painterly / hand-drawn textures

Watercolor and brush fills (p5.brush-style) are GPU-heavy: seconds per frame without a
dedicated GPU. Offer a lighter texture (flat fill + grain + rough outline) when the machine
has no dedicated GPU, and render the textured version only for the final.

## 4. Never crop the character

Illustrated characters must always be shown whole — hands, feet, antennae. Use
`objectFit: "contain"` on a matching background (never `cover`) for character images, keep
≥ 6 % margin inside their box, and when cutting one character out of a group image, cut at a
natural seam (e.g. the middle of a handshake). Check the frame where the character is
largest (overshoot, punch-in).

## 5. Third-party characters

Mascots belong to their owners (e.g. Clawd belongs to Anthropic). Use them for study and
personal tests only; for client work, create the client's own character with them, store its
rig file, and reuse that file for every episode so the character stays consistent.

## 6. Review

Contact sheet per scene (≥ 1 frame every 0.5 s) before the full render; check model
consistency, arcs, holds, and that no limb leaves the frame.
