# Scene Recipes

Proven scene structures distilled from ~80 long, director-grade prompts in the
awesome-opus5-5-videos corpus (Oct 2026; see `reference-library.md`) plus classic motion
craft. Each recipe: **intent → structure → numbers → Remotion/kit mapping → gotchas**.
Numbers assume 30 fps unless noted; the corpus mostly rendered at 60 fps — keep the
*seconds*, not the frame counts.

Pick 1–2 recipes per video during the Concept step. A recipe is a skeleton; the project's
direction (palette, type, metaphor) is what makes it original. Credit-worthy sources are
listed by slug so you can study the original prompt, never to copy its brand or assets.

---

## 1. One shape, never cut — UI morph loop
**Intent:** product/UI story with total continuity; "everything is one object".
**Structure:** one element morphs size, radius, color (and position) through 5–12 states;
content swaps inside it; a cursor causes every change; the camera keeps each state large
(state ≈ 50% of frame); last frame = first frame.
**Numbers:** states on a beat grid (120 BPM → 0.5 s beats, a state per bar or per 2 beats);
morph 0.5–0.8 s; content swap ≈ 12 px blur over ~0.15 s; content enters after the container
starts and leaves before the next morph; springs with at most a tiny overshoot (damping
ratio ~0.7).
**Kit:** `MorphBox` (states), `Cursor` (clicks 2–4 frames before each change), `Typewriter`,
`CountUp`, `beatPulse` for a micro-breath, `springSteps` for values with several targets.
Working example: `showcase/.../UiMorph.tsx` (8 s seamless loop, states on measured downbeats).
**Gotchas:** text inside a morphing shape needs its own clip and its own enter/exit timing;
never stretch artwork when the container changes aspect; start each morph ~2 frames before
the beat so the visual hit lands on it; check the seam (`rhythm-audit --loop`).
**Lessons from our own critic loop (round 1 scored 4/10):** keep ONE fill color for every
state — a white↔black lerp passes through a grey that reads as "disabled"; the shape stays
solid and sharp, only its content swaps (leave in the first ~25% of the morph, enter after
~60%); a counter and its arc/bar must read the same value; give each state equal time on the
grid (2 s per state at 120 BPM) instead of a long idle; the payoff state must visibly *play*
something, never an empty card with a play icon; put the loop seam inside a morph (a state
with a negative `at`) so frame 0 is already in motion.
Rounds 2–3 added: a morph must read as GEOMETRY, not a dissolve — content blur ≤ 4 px, old
content gone by ~30% of the morph, new content only once the shape is ~80% there, a tiny
2-frame overshoot (`ease.overshootSoft`); every click needs a visible target (the ring's
number becomes a ▶ at 100%, the card grows a "Gerar outro" chip); a hover/press is a real
reaction (scale 0.94 → spring release, the icon turns), never a content swap; start the loop
a few frames into the seam morph so the poster frame (frame 0) is sharp.
Round 4 added the step from "good" to "premium": **carry the accent through every morph**.
One accent-colored carrier travels (13 frames, `ease.inOut`, slight arc) from the element
just clicked to the accent of the next state — send ↑ → ring head → ▶ grows into the card's
disc → disc shrinks into the ✦ → ↑ — while the source hides at hand-off and the target
appears when the carrier lands. Compute the target from the SAME function that draws it
(e.g. the disc's path) so the landing is pixel-exact. Kit: `Handoff`.
Round 6 polished the ends: the carrier draws the SOURCE glyph shrinking away (4 frames) while
the dot grows under it at full opacity, and the TARGET glyph growing in over the last 5 frames
(stars rotate −45° → 0°) — static elements switch on the hand-off frame with no pop. Measure
glyph positions from a rendered still (our eyeballed ✦ was 6 px off).
*Slugs:* twoclipping-402193, annacher-152174, 0xnicc0-516612, flxrnc-251921, thegrootdev-966114.

## 2. Continuous take — every gesture moves the camera into the next world
**Intent:** a premium "one-shot" product film; each action motivates the next shot.
**Structure:** a press, swipe or drag doesn't just change UI — it pulls the camera (rubber-band
out of an app, dive into a chart point, an app floods out of a button). One gesture per scene.
**Numbers:** morph + camera share one curve, e.g. cubic-bezier(.45,0,.15,1) over ~0.8 s;
content dissolves in the back half of the glide; quiet intro, the key press lands on the drop.
**Kit:** `Camera` + `Layer`, `springSteps` with `CAMERA_SPRING`, `IrisReveal`/flood (recipe 9).
**Gotchas:** never zoom in then straight back out; never reverse camera direction mid-move;
interpolate zoom in log space for big scale changes (`Math.exp(tween(...log values))`).
*Slugs:* rossaxbt-312793, twoclipping-762046.

## 3. Accent thread — one colored element carries the whole film
**Intent:** cohesion; the eye always knows where to look.
**Structure:** a single accent dot/shape is the only saturated thing on screen. It becomes a
toggle, the dot on an "i", a graph point, a frame-filling circle, the end-card mark.
**Numbers:** accent ≤ ~10% of pixels; never crossfade ink into the accent — move the accent
element between states instead.
**Kit:** `MorphBox` or plain divs driven by `springSteps`; `IrisReveal` from the dot's position.
*Slugs:* rossaxbt-707651, koushikde-937635, verbove-268381, notdwd-998633 ("the button is the only saturated colour").

## 4. Cursor drives the real UI
**Intent:** demos that read as cause → effect; credibility ("real product, real data").
**Structure:** real clicks, typing, one drag, hovers with tooltips. Drags are direct
manipulation: the value follows the cursor; on release it springs from where it was.
**Numbers:** cursor ≤ ~65 px/frame at 60 fps (≈ 130 px/frame at 30); aim where the target
WILL be; click 2–4 frames before the state change; human typing 12–18 chars/s, caret blinks
only when idle; each feature on screen ≥ 2.5 s so viewers can follow.
**Kit:** `Cursor` (arc travel, press + ripple), `Typewriter`. Screen-recorded UI: `<Video>` /
`<OffthreadVideo>` inside a device or card, zoomed with `Camera`.
**Gotchas:** every number/label on screen comes from the real product (recordings,
screenshots) — never mock data; keep the cursor tip locked to what it drags.
*Slugs:* bilimfili1-459762, twoclipping-496100, twoclipping-747965, notdwd-998633, howdevelop-733090.

## 5. Liquid tab / stretchy toggle — dual-edge springs
**Intent:** UI that feels physical without bouncing.
**Structure:** the indicator's left and right edges ride different springs; the leading edge
moves first and stretches, the trailing edge catches up.
**Numbers:** leading edge stiffer (settle ~0.25 s), trailing softer (~0.4 s).
**Kit:** two `springSteps` with different configs → `left`, `right` of one div.
*Slugs:* twoclipping-402193, annacher-152174, verbove-268381.

## 6. Overdrag rubber-band
**Intent:** playfulness and physicality in sliders/scrubbers.
**Structure:** dragging past the max stretches the track/knob (resistance grows), release
snaps back with a spring. Can also pull the camera out of a scene.
**Numbers:** visual overshoot ≈ 30–50% of the drag excess (resistance curve `x / (1 + x/limit)`).
*Slugs:* twoclipping-402193, annacher-152174, flxrnc-251921, rossaxbt-312793.

## 7. Number reveal / counters
**Intent:** proof — revenue, users, speed, percentages.
**Structure:** digits roll while something moves, then settle sharply; unit as part of the
design (`12x`, `R$ 49`); optional "▲+value" pop after the land.
**Numbers:** roll 0.8–1.5 s; tabular figures; hold the final value ≥ 1 s.
**Kit:** `CountUp`.
**Gotchas:** counters read the frame's time (not motion-blur subframes) or digits smear;
counters that should keep running through cutaways run on the global clock.
*Slugs:* twoclipping-551116, twoclipping-747965, flxrnc-251921, op7418-814408, notdwd-998633.

## 8. Kinetic type: mask rise, word-per-beat, weight swing
**Intent:** the message IS the visual (hooks, manifestos, lyric lines).
**Structure options:** words rise through a mask line; one word per beat; weight swings
thin→black on the hit; per-glyph springs on y/opacity/blur; the outgoing word's shape masks
the incoming one; vertical roll for word swaps; scramble that locks on the beat.
**Numbers:** word pull-up ≈ 20 px → 0 over 0.6 s, stagger 0.08 s, cubic-bezier(.16,1,.3,1);
1/16-note stagger at 120 BPM = 125 ms; text being read ≥ 64 px tall on 1080; a reading hold
of ~0.7 s on the completed phrase; at least one ~400 ms moment of total stillness at the key
line.
**Kit:** `MaskReveal`, `WordStagger` (mode "mask"), `CharCascade`, `Scramble`, `TrackingIn`.
**Gotchas:** motion blur never on text being read; no ornamental travel before the reading
hold ends; rotate whole glyphs, don't morph glyph paths between unrelated words.
*Slugs:* gdgtify-989608, gdgtify-130294, techhalla-498547, koushikde-937635, twoclipping-000267.

## 9. Flood / iris transitions
**Intent:** shape-driven scene changes that feel designed, not "transition preset".
**Structure:** a shape (often the accent circle or a UI element) floods edge to edge, then the
next scene opens from it; or an iris (circle/hexagon) closes onto a point and opens the next scene.
**Numbers:** flood ≈ 0.3–0.35 s, overscaled past the corners; give it a soft start (a hard
ease-out flood reads as a jump); ease a closing iris by AREA (radius ∝ √t), not radius.
**Kit:** `IrisReveal` (cx/cy at the focal point); for floods, a circle scaled with `tween`
then swapped for a full-frame rect once covered.
**Gotchas:** never zoom the camera into an off-centre dot — open the dot as a mask instead;
let the flood fully retreat before the next scene's motion begins.
*Slugs:* twoclipping-496100, twoclipping-747965, twoclipping-551116, ultimaxbt-549714, heyiamnick-119558.

## 10. Beat-cut promo
**Intent:** high-energy launch/ad on music.
**Structure:** measure the track (`beat-map.mjs`); hook on bar 1; a hook word morphs into the
product on bar 2; the reveal on the drop; then ONE move per bar (wall of clips → big type →
3D carousel whip → stats on push cuts → logo).
**Numbers:** 120 BPM → 2 s bars; something happens on every beat for the first 16 beats, then
every other beat; cuts on downbeats; moves start ~0.05 s before the beat to land on it.
**Kit:** `beatPulse`, `snapToBeat`, `beatIndex`; `rhythm-audit --beats` to verify.
**Gotchas:** don't step rotations once per beat (reads as stutter) — rotate continuously;
don't force SPEECH onto a beat grid — use a phrase cue sheet for voice.
*Slugs:* twoclipping-000267, twoclipping-551116, ultimaxbt-549714, techhalla-498547.

## 11. Silence → payoff
**Intent:** tension and release; makes one moment unforgettable.
**Structure:** a deliberately quiet, slow build (darkness, a mechanism assembling, a single
sound), then the payoff: the drop, the first hit, the reveal — then silence again.
**Numbers:** build 8–14 s in a 20–30 s piece; the payoff is the loudest/brightest frame.
*Slugs:* adrianduta96-992248, agioyaz-397647, rossaxbt-312793.

## 12. Camera through space / scale journey
**Intent:** scale and wonder; "zoom from a dot to a world".
**Structure:** start on a single dot → windows/objects arrive → pull back until the whole
system is a point → dive into a new context. Or fly through a tunnel / over a landscape.
**Numbers:** pushes/pulls 1.5–3 s on gentle ease-in-out — about half the speed you'd pick
first; one eased move per scene; zoom in log space.
**Kit:** `Camera` (zoom/x/y), `Layer depth` for parallax; real 3D → `@remotion/three`.
**Gotchas:** never zoom in and straight back out; keep text out of fast camera moves.
*Slugs:* dale-vaz-879074, jake11moran-414633, koushikde-937635, egeberkina-949521.

## 13. Seamless loop
**Intent:** feeds and landing pages that replay forever.
**Structure:** last frame = first frame: geometry, content, camera, cursor position AND
velocity. A loop can START anywhere — open on its strongest moment.
**Numbers:** loop length = whole bars of the music; export [0, duration) without duplicating
the endpoint frame.
**Kit/Remotion:** design the timeline so state N = state 0, then rotate the start with two
offset `<Sequence>`s (see `UiMorph.tsx`). Verify with `rhythm-audit --loop`.
**Gotchas:** rotating patterns need speeds that land on the same pattern at the end; reset
hidden elements only while they're fully occluded; micro-breath (scale 1 → 1.012 → 1) keeps
holds alive without breaking the seam.
*Slugs:* thegrootdev-966114, twoclipping-551116, gdgtify-929495, flxrnc-251921, 0xkarmi-129839.

## 14. Shared hero object across cuts
**Intent:** continuity between different scenes (match cut).
**Structure:** one object (cover art, a heart, a button, a card) keeps identity across
search → detail → tile → zoom; carried objects land on the same pixels on both sides of a cut.
**Kit:** compute the object's rect once (or measure it), animate it in a layer above both
scenes, cut the scenes underneath. Same technique as the accent carrier in recipe 1: hide the source at
hand-off, show the target when the carrier lands, derive both positions from one function.
*Slugs:* brainextends-606193, everestchris6-399895, ultimaxbt-549714.

## 15. Mechanism as proof — explainers ("simulate, don't draw")
**Intent:** explain something true so it's understood, not just illustrated.
**Structure:** the animation IS the process: a real random walk, marbles that compute, waves
traveling at real speeds, a query traced through real code. Comparison states (A vs B on the
same input) and sliders between extremes.
**Numbers:** real values with honest uncertainty; a facts file with sources is the only source
of on-screen numbers; copy readable without audio.
**Gotchas:** don't compute the answer separately and fake the mechanism; state caveats on
screen when the logic has limits.
*Slugs:* gdgtify-393073, godsboy7777-150194, astrothewizard-618782, egeberkina-949521, deedydas-407965, apoorvjain25-945542.

## 16. Reward / highlight moment
**Intent:** a single climactic beat (unlock, purchase, level-up, milestone).
**Structure:** idle → anticipation charge (~1 s, rising tension) → burst → reveal → settle.
**Numbers:** squash/stretch + overshoot allowed HERE; confetti once, at the peak; bloom ≤ 0.8;
shockwave as 3 strokes (wide faint, medium, thin bright).
*Slugs:* op7418-814408.

## 17. Exploded view (3D object)
**Intent:** "how it works" for hardware, engines, products.
**Structure:** assembled hero rotation → parts slide apart along their axis with labels →
highlight one part with one line of copy → snap back together.
**Kit/Remotion:** `@remotion/three`; part offsets via `springSteps`; labels as DOM over the canvas.
*Slugs:* aichrislee-922082, aichrislee-479847, mrkindey-267498.

## 18. Typography as architecture
**Intent:** poster-like, editorial statements with weight.
**Structure:** words take physical roles — a baseline becomes an orbit, words act as lintel,
load, support; transitions by occlusion or matched edges, never by point interpolation.
**Numbers:** ≥ 64 px for the phrase being read; 700 ms hold on the completed phrase; final
1.2 s completely still.
*Slugs:* gdgtify-989608, gdgtify-130294.

---

## Default prohibition list (start here, then adapt per brand)

Ranked by how often director-grade prompts banned them: particles/bursts as decoration ·
random crossfades and "transition presets" · bouncy/elastic easing · dead time / frozen
holds > 1 s · anything that looks like a template · stock footage and fake dashboards/HUDs ·
gradients on UI chrome · glows/neon · camera shake · lens flares · random glitch/RGB split ·
overlapping text · 3D flips in a 2D film · invented features, numbers or testimonials ·
generic AI clichés (brains, robots, sparkles) · zooming in then straight back out.

Allowed only with a reason: glitch for 1–2 frames on a real cut with a sound; chromatic
misregistration ±2–4 px on impact frames; confetti once at a reward peak.

## Technical gotchas (hit by others so you don't have to)

- `will-change` on anything the camera scales → blurry text. Don't.
- Opacity/filter on a `preserve-3d` element flattens it (both faces show): fade a wrapper.
- Measure element positions for match cuts instead of guessing coordinates.
- Motion-blur subframes: 4 can ghost on fast whips; use 8 samples for whips (`CameraMotionBlur samples={8}`).
- Footage inside designs: premount it and let Remotion seek (`<Video>` from `@remotion/media`);
  never rely on real-time playback.
- Looping "breathing" values must be pure functions of the frame (no accumulated state).
- SFX: align the sound's measured transient peak — not the file start — to the event.
