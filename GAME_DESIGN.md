# TinyWorld — Game Design & Roadmap (the "make it addictive" plan)

This doc is the creative/strategic brain for the next stage: **what to build, how it should feel, and a
fully prioritized TODO list** to turn the working MVP into an interactive, addictive little game that
wins the Thousand Token Wood track. It does NOT change the hard rules in `AGENTS.md` (sponsor models
only, ≤4B each, mock-first, commits via Codex). Use it alongside `BUILD_GUIDE.md` (UI/build specs) and
`CHECKPOINT.md` (current state).

---

## 1. North Star — the one-sentence experience

> *"I threw one weird event at a tiny town, five little people reacted in ways I didn't see coming, and
> now I HAVE to throw another one to see what happens to them."*

Everything below serves that loop. If a feature doesn't make the player say **"I didn't expect that"**
or **"that is SO Marta"**, it's a distraction — defer it.

---

## 2. The Addiction Engine (research → applied)

Five forces make sandbox/sim games compulsive. Map each to a concrete TinyWorld mechanic:

| Force (from research) | In TinyWorld | Status |
|---|---|---|
| **Variable reward / unpredictability** | The 4-layer system (mood + memory + relationships + surprise seed) → reactions never repeat | ✅ built |
| **Emergent storytelling** (player authors the story) | Characters reference each other; rivalries flare; crushes act up → mini-dramas the player narrates | ⚠️ partial — strengthen relationship cross-talk |
| **Compounding discovery** (small rewards build into systems) | A **relationship web + per-character "vibe meters"** that visibly shift after events → consequences accumulate | ❌ to build |
| **Identity / "that's so them"** | Strong, distinct personas (we have 5 good ones) + a **catchphrase/quirk** surfacing over time | ⚠️ deepen |
| **Social proof / shareability** | A **"Today in TinyWorld" recap card** (screenshot-ready) + multiplayer guessing | ❌ to build |

### The single biggest upgrade: make events have *consequences*
Right now each event is independent. Borrow Smallville's **memory + emergent reaction**: after an event,
let one character's reaction become the *seed of the next beat*. Two cheap mechanics:
1. **Consequence chain** — after reactions, with some probability auto-generate a short follow-up
   ("Because Jay tried to impress Nia, Marta now…") so the world feels alive between the player's inputs.
2. **Relationship drift** — each event nudges relationship/vibe values (friend↔rival, mood baseline),
   shown as a glowing line in a **relationship web**. The player *sees the town changing because of them.*
   This is the "compounding discovery" hook and it's mostly bookkeeping on top of what exists.

---

## 3. Inspiration Map (what we borrow, concretely)

- **Smallville / Generative Agents** → memory + tiny reflection: every ~5 events, each character forms a
  one-line "reflection" ("I keep noticing the street is changing") that subtly colors future reactions.
  *Don't* build full 25-agent planning — we have 5 and a player-driven loop; that's the right scope.
- **The Sims** → relationship/mood meters as readable HUD bars; characters as expressive little sprites.
- **Stardew / cozy iso sims** → warm 2.5D isometric world, day/night, ambient life (idle bobbing, swaying
  trees) so the town feels lived-in even when idle.
- **Party/guessing games (Wavelength/Jackbox)** → the pass-and-play "predict the reaction" mode is the
  social, replayable, shareable layer. High ROI for Community Choice votes.
- **Game juice** → every action gets feedback: trigger = map shockwave + brief screen-shake; reaction =
  bubble spring-in + soft pop SFX; meter change = number ticks up with a glow.

---

## 4. Game-Feel / Juice Checklist (cheap, high-impact)

- [ ] Map **shockwave ring** emanating from town center on Trigger (move the existing `ripple` onto the map)
- [ ] Subtle **screen-shake** (~150ms) on Trigger and on a "Chaos" event (bigger shake)
- [ ] Speech bubbles **spring in staggered** (50ms apart) — feels like the town "answering" one by one
- [ ] **Typewriter reveal** of bubble text (reads as characters "speaking")
- [ ] **Active-speaker glow ring** under whoever's voice is auto-playing
- [ ] Button **squish on press**, **pulse/glow on hover** (partly done)
- [ ] Soft **SFX**: a "whoosh" on trigger, a "pop" per bubble, a chime on meter change (tiny CC0 wavs, optional autoplay)
- [ ] **Number/meter tick** animation when vibe meters change
- [ ] **Day/night tint** drifting over the map (ambient life)
- [ ] Idle: characters gently **bob**, trees **sway** (pure CSS keyframes)
> Guardrail from research: juice must echo core gameplay; don't over-shake or it annoys. Keep it tasteful.

---

## 5. UI/UX Vision — "a real game, not a form"

Base look is specified in `BUILD_GUIDE.md` §1 (Cozy-Future Pixel Art) + the isometric upgrade I gave
earlier. The game-UI framing to add:

- **Isometric 2.5D board** (rotateX/rotateZ + upright character billboards) — the #1 "it's a game" change.
- **Character roster rail** (left or bottom): 5 portrait cards, each with name, mood emoji, and 2 small
  **vibe meters** (e.g. Energy, Social) that animate after events — this is the HUD that sells "sim game".
- **Relationship web overlay** (toggle): nodes = characters, glowing lines = friend/rival/crush, line
  thickness/color shifts as relationships drift.
- **Top status ticker**: "Day 3 · 12 events · Chaos meter ▮▮▮▯▯" — gives progression & a goal to chase.
- **Event composer** as a game console: big input, mic, 🎲 Chaos, and a **Scenario picker** (Learn mode).
- **Recap card**: a "📸 Share today" button renders a clean image-style summary of the funniest reactions.

---

## 6. Feature Concepts, Ranked by (Addictiveness ÷ Effort)

1. **Consequence chains + relationship/vibe drift** — biggest "alive world" payoff, mostly state bookkeeping. ⭐⭐⭐⭐⭐
2. **Character roster HUD with animated vibe meters** — makes change *visible*; strong game-UI signal. ⭐⭐⭐⭐⭐
3. **Map shockwave + screen-shake + staggered bubbles + typewriter** (juice bundle). ⭐⭐⭐⭐⭐
4. **Isometric board** — transforms the look. ⭐⭐⭐⭐
5. **"Chaos meter" progression + unlock chaos events after N** — a goal to chase. ⭐⭐⭐⭐
6. **Multiplayer pass-and-play guessing** — social/replayable/shareable; great for Community Choice. ⭐⭐⭐⭐
7. **Tiny reflections (Smallville-lite)** every ~5 events. ⭐⭐⭐
8. **Recap/share card** — virality. ⭐⭐⭐
9. **Day/night + ambient idle life** — cozy polish. ⭐⭐⭐
10. **Learning mode + "why did they react?" explainer** — educational angle (teacher use-case). ⭐⭐⭐
11. **Sprite art (Kenney CC0 or FLUX-generated)** — wow factor + BFL sponsor angle. ⭐⭐⭐ (stretch)
12. **Click-to-place builder / character creator** — most effort, least demo payoff. ⭐⭐ (defer)

---

## 7. TODOs

### 🔴 IMMEDIATE (do next — gets us to a winning demo)
- [ ] Confirm **Modal migration** (in progress) runs the demo end-to-end; keep `TINYWORLD_MOCK` path working as fallback.
- [ ] **Map shockwave on Trigger** (move `ripple` from event panel onto `.tw-map`) + light screen-shake.
- [ ] **Staggered bubble spring-in + typewriter reveal** of reaction text.
- [ ] **Character roster HUD**: 5 portrait cards with mood + 2 animated vibe meters.
- [ ] **Relationship/vibe drift**: after each event, nudge per-character mood baseline + pairwise relationship value; persist in `unpredictability.py` state.
- [ ] Verify the **"I didn't expect that" bar**: trigger same event 3× → clearly different, in-character, occasionally surprising reactions. If flat, strengthen `SURPRISE_SEEDS`.

### 🟠 IMPORTANT (core to "addictive", do after immediate)
- [ ] **Consequence chain**: optional auto follow-up beat referencing a prior reaction (probabilistic).
- [ ] **Isometric 2.5D board** + upright character billboards + ground shadows.
- [ ] **Chaos meter + progression ticker** ("Day N · events · chaos"); unlock chaos events after 5.
- [ ] **Relationship web overlay** (toggle) with glowing friend/rival/crush lines that shift over time.
- [ ] **Multiplayer pass-and-play guessing** mode (no websockets; rounds + scoring + leaderboard).
- [ ] **Recap "📸 Share today" card** (renderable summary image/HTML) for social/Community Choice.

### 🟡 NICE-TO-HAVE / STRETCH
- [ ] **Smallville-lite reflections** every ~5 events feeding back into prompts.
- [ ] **Learning mode** scenarios + "why did they react?" explainer (uses MiniCPM) — teacher/classroom story.
- [ ] **Day/night tint + ambient idle** (bobbing characters, swaying trees).
- [ ] **Sprite art**: swap CSS tiles for Kenney CC0 sprites *or* generate isometric sprites with **FLUX.2-klein** (adds Black Forest Labs sponsor + custom art) — ship as static PNGs, zero runtime cost.
- [ ] **Sound design**: whoosh/pop/chime CC0 SFX.
- [ ] Click-to-place builder + in-app character creator (only if everything else is solid).

### 🟢 JUICE / POLISH PASS (do near the end)
- [ ] Active-speaker glow ring; meter-tick animations; button squish; hover pulse.
- [ ] Empty/idle state copy ("the town is quiet…"); loading "neighborhood is waking up…" state.
- [ ] Mobile responsive check (judges may open on phone).

### 🏆 SPONSOR / PRIZE TODOs (don't lose free points)
- [ ] **OpenBMB**: MiniCPM5-1B (agents) + VoxCPM2 (voices) credited in UI + README. ✅ in stack
- [ ] **NVIDIA**: Nemotron-3-Nano-4B explicitly named in README ("powers Nia & Priya"). 
- [ ] **Cohere**: Transcribe mic input working + credited.
- [ ] **Modal**: parallel inference; show a "sequential vs parallel" latency note in README. (in progress)
- [ ] **OpenAI Codex**: public GitHub repo with **Codex-attributed commits**; repo linked in Space README.
- [ ] **Black Forest Labs** (optional): FLUX-generated sprites/logo → 5th sponsor.
- [ ] **Tiny Titan badge**: confirm every model ≤4B in README param table.
- [ ] **Community Choice**: shareable recap card + a punchy demo clip.

### 📤 SUBMISSION CHECKLIST
- [ ] Deployed Space under `build-small-hackathon` org; runs cold without manual steps.
- [ ] README: frontmatter tags, hook blurb, how-to-play, model param table (≤32B), GitHub link, demo video.
- [ ] `COHERE_API_KEY` + Modal token as **Space secrets** (never committed).
- [ ] 60–90s **demo video** of the magic moment recorded + linked.
- [ ] Social post (X/LinkedIn/HF) for Community Choice votes.
- [ ] Final "demo moment 3× in a row, no traceback" smoke test on the live Space.

---

## 8. Guardrails (so we don't lose the deadline)
- ~2 days left. **Ship the 🔴 IMMEDIATE list first and re-submit**, then layer 🟠 IMPORTANT, then stretch.
- Every new mechanic must be **mock-testable on CPU** (`TINYWORLD_MOCK=1`) and must **degrade gracefully**.
- Don't let the builder/creator features (lowest ROI) eat time reserved for juice + the addiction loop.
- After each chunk: update `CHECKPOINT.md`, leave commits to Codex.

---

### References / inspiration
- Generative Agents (Smallville) — memory, reflection, emergent behavior: arxiv.org/pdf/2304.03442 · github.com/joonspk-research/generative_agents
- Emergent storytelling & sandbox replayability — gamedeveloper.com, gamerant.com
- Game juice / game feel — gameanalytics.com, bloodmooninteractive.com/articles/juice.html
- Cozy isometric design — juegostudio.com isometric guide, IsoCity (open-source iso city builder)
