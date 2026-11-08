# Other animation skills: when to hand a scene to one, and what to borrow

Nine open-source Claude Code skills for animation (repos checked by the guide "9 skills do Claude
pra criar animações", 2026-11-05). None is Anthropic's. This skill stays the director and the
editor (Remotion, voice, captions, sound, spacing); a sibling renders **one scene** when its
medium fits better, and the MP4 comes back into the Remotion timeline as footage.
Install only when the user asks; read each LICENSE before paid use.

| skill | best for | install | borrow even without it |
|---|---|---|---|
| **whiteboard-video** (Matteoikarieth96/whiteboard-video-skill) | narrated whiteboard explainer, marker paced to the voice, 16:9 or `--vertical` | `git clone --depth 1 https://github.com/Matteoikarieth96/whiteboard-video-skill ~/.claude/skills/whiteboard-video` + `npm install` in `scripts/` | interview → scene-by-scene script with **every number checked in 2 sources** → approval → voice samples → draw |
| **Claude Animation Base** (JohnHeibel/ClaudeAnimationBase) | hand-painted character (p5.brush), 31 emotions, brush transitions | clone + `npm install`, open Claude Code in that folder | storyboard first, contact sheet per scene; swap watercolor washes for flat fills on machines without a GPU (seconds per frame otherwise) |
| **Claude Drawing** (cloveric/claude-drawing-skill) | a painting made in code (77 styles) recorded **stage by stage** | clone into `~/.claude/skills/claude-drawing` (numpy + Pillow) | "painting in progress" reveal: stages (line → color blocks → texture → final) + a progress card "01 / 04" |
| **Anidoodle** (alexgreensh/anidoodle) | stroke-by-stroke drawing timelapse, 32 styles, loop GIF, launch-film kit in 16:9/1:1/4:5/9:16 | `/plugin marketplace add alexgreensh/anidoodle` → `/plugin install anidoodle@alexgreensh-anidoodle` | draw in the order an illustrator of that style would; gate + verify-export before delivery |
| **Motion Skill** (LunaAI519/motion-skill) | retro paper collage animated by AI (Nano Banana keyframe + Kling) — **the only paid one** (~US$ 4 per 30 s) | clone into `~/.claude/skills/motion` + 2 MCP servers | show the keyframe **and the credit cost** and wait for OK before generating; no real faces, no brand logos; ask for Portuguese labels |
| **Motion Design Skill** (LottieFiles/motion-design-skill) | timing judgment for any web animation (no renderer) | `npx skills add LottieFiles/motion-design-skill -g -a claude-code` | duration and easing tables, hero-first then stagger, say which curve and why |
| **Manim Skill** (adithya-s-k/manim_skill) | math, formulas, proofs, 3Blue1Brown-style transforms | `npx skills add adithya-s-k/manim_skill -g -a claude-code` + Manim via uv | one shape becomes the next in view; render `-ql` to check, `-qh` final; `--resolution 1080,1920` for Reels; MathTex needs LaTeX |
| **JavaScript Animation** (iart-ai/javascript-animation-skills) | hand-drawn short in one HTML canvas, no images, soundtrack composed in Web Audio cut on the beat | `/plugin marketplace add iart-ai/javascript-animation-skills` → install | audit "zero ready-made images"; contact sheet per scene |
| **Huashu Art Motion** (alchaincyf/huashu-art-motion) | one scene travelling through art styles with film transitions; 9 explainer grammars | `npx skills add alchaincyf/huashu-art-motion -g -a claude-code` | a script that **measures cuts, rhythm and motion of a reference** (compare with our `rhythm-audit.mjs`); the camera never stops |

Prerequisites shared by most: Node 22.20+ (npx skills), ffmpeg, Python 3.9+, uv, Chrome
(`CHROME_PATH` if installed elsewhere). A skill that does not show in `/skills` is not called —
name it in the request.

## Bringing a sibling's scene into our edit

Each skill exports a different size. Normalize to the reel before editing (brand color in the
pad, never black bars on a light identity):

```bash
for f in cena*.mp4; do ffmpeg -y -i "$f" -an -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0xFAF9F5,fps=30,format=yuv420p" -c:v libx264 -crf 18 "norm_$f"; done
```

Then use them as `OffthreadVideo` shots in Remotion so captions, SFX, spacing pass and the
follow card stay ours. A 16:9 scene in a 9:16 reel gets a layout (title above, scene in the
content zone), not a letterbox.

## Cost and time to quote

- Code-drawn skills (8 of 9): R$ 0 per render beyond the Claude plan; the cost is plan usage
  while Claude writes and checks hundreds of lines — start with 15–30 s pieces.
- Painted characters: 30 s at 24 fps = 720 frames; at ~2 s/frame without a GPU ≈ 24 min —
  always a contact-sheet preview first.
- Motion Skill: 6 Kling clips of 5 s ≈ 45 credits + 6 keyframes ≈ US$ 4.2 per 30 s, plus the
  subscriptions; generated clips never refund credits.
- Voice: a 30 s narration ≈ 75 words / 450 characters (fits ElevenLabs' free tier; commercial
  use needs a paid plan).
