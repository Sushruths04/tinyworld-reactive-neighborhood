# TinyWorld V2 — Complete Redesign & Execution Plan (Codex-ready)

This is the authoritative plan for the V2 redesign. It supersedes the MVP layout where they conflict.
It still obeys `AGENTS.md` (sponsor models only, runtime models ≤4B, **mock-first**, **commits via Codex
only**). Read order for any agent: `AGENTS.md` → this file → `GAME_DESIGN.md` (the "why") → `CHECKPOINT.md`.

> **Decisions locked by the owner:** FLUX diorama visual style · lean Party Mode IN · full Learn mode IN ·
> multiple playgrounds/scenarios IN. Owner has time and wants maximum winning chances.

---

## 0. North Star & unique hook (say this in the demo & README)

**TinyWorld — "the town that remembers."**
*Throw a pebble into a tiny town and watch the ripples turn into stories.*

You don't control the residents. You change the town's **weather** (events). Five AI residents react
unpredictably, **remember** what happened, **gossip** (reactions spread between them), and their
**relationships drift** over time — so the town visibly changes because of you. Single-player sandbox,
4-player party guessing, or classroom Learn mode. Multiple themed **Worlds** to play in.

**Why it wins / how it differs from peers (e.g. mAIndlock):** social & emergent (a whole town, not one
mind), light & funny & shareable (not dark escape-room), multi-world content, real voices (VoxCPM2),
voice input (Cohere), and a *visible* living-world state — all with **one cheap LLM call per character**
(low complexity, high "alive" payoff).

---

## 1. New app layout (the redesign — be exact)

Replace the current stacked layout with a **3-zone game HUD + docked console**. Dimensions in `()` are
column scale hints for Gradio.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ TINYWORLD   [ World ▾ Maple Street ]      Day 3 · ⚡12 events · Chaos ▮▮▮▯▯ │  TOP BAR
├──────────────┬───────────────────────────────────────────────┬────────────┤
│ ROSTER RAIL  │              THE STAGE  (diorama)              │  TOWN LOG  │
│  (scale 3)   │                 (scale 6)                      │ (scale 3)  │
│ 5 portrait   │  rendered isometric world art (FLUX PNG)       │ scrolling  │
│ cards:       │  + avatars standing on hotspots                │ feed of    │
│  portrait,   │  + comic speech bubbles (typewriter)           │ reactions, │
│  name, mood, │  + active-speaker glow ring                    │ gossip &   │
│  2 vibe bars │  + [toggle] relationship-web overlay           │ drama      │
│  (Energy,    │  + day/night + town-mood tint                  │ beats      │
│   Social)    │                                                │            │
├──────────────┴───────────────────────────────────────────────┴────────────┤
│ EVENT CONSOLE:  [ type an event… ]  🎤mic   ⚡Throw   🎲Chaos   🎭Scenario ▾  │  DOCKED
│ Mode tabs:  ( 🎮 Solo | 👥 Party | 🎓 Learn )      🔊 auto-voice   👤 hear ▾   │  BOTTOM
└────────────────────────────────────────────────────────────────────────────┘
```

- **Stage is dominant** (≈60% width). Roster left, Town Log right.
- **Mode tabs** swap the console's behavior (Solo/Party/Learn) — same stage, different interaction.
- **World picker** (top bar) switches playground → reloads diorama, cast, hotspots, scenarios.
- **Responsive (<900px):** Stage on top full-width; Roster & Town Log become two tabs; console docked below.

Implementation: build the stage as **layered HTML/CSS inside `gr.HTML`** (background `<img>` + absolutely
positioned avatar/bubble `<div>`s) — a "canvas-like" custom render WITHOUT a real canvas engine (less code).
A thin `assets/map.js` handles animations (slide, typewriter, shockwave, bubble auto-dismiss).

---

## 2. Data model (the foundation refactor — do this FIRST)

Everything becomes **data-driven per World** so content is cheap to add. Create `worlds/` package.

### 2.1 World schema — `worlds/__init__.py` exposes `WORLDS: dict[str, World]`

```python
# worlds/maple_street.py  (one file per world; same shape)
WORLD = {
    "id": "maple_street",
    "name": "Maple Street",
    "theme": "cozy modern suburb",
    "diorama": "assets/worlds/maple_street.png",   # FLUX-generated, see §6
    "palette": {"tint_day": "#fff3d6", "tint_night": "#1a2342"},
    "hotspots": {                                   # normalized %, (x,y) on the diorama
        "marta_home": [12, 64], "cafe": [70, 40], "park": [48, 30],
        "square": [50, 55], "jay_home": [85, 70], "school": [30, 25],
    },
    "cast": [ ... 5 characters ... ],              # SAME schema as current characters.py
    "scenarios": [ ... ],                          # Learn-mode scenarios, see §5.3
    "events": [ ... ],                             # world-flavored chaos events
}
```

### 2.2 Character schema (extend current `characters.py` shape)
Keep existing fields (name, age, job, traits, backstory, relationships, voice_description, model) and ADD:

```python
"emoji": "🧓",                 # avatar (MVP); later: "sprite": "assets/avatars/marta.png"
"home": "marta_home",          # hotspot key where they idle
"catchphrase_hint": "always compares things to the past",  # flavor for prompts
# runtime state lives separately (see §3), NOT hard-coded here
```

### 2.3 Runtime world-state — extend `unpredictability.py` (or new `world_state.py`)
Per active world, hold mutable state (reset on world switch):
```python
state = {
  "day": 1, "event_count": 0, "chaos": 0.0, "town_mood": 0.0,  # -1..+1
  "vibes":   { name: {"energy": 0.6, "social": 0.5} },          # 0..1 each
  "affinity": { (a,b): 0.0 },                                   # -1..+1 pairwise
  "moods":   { name: "curious" },                               # existing
  "memory":  { name: deque(maxlen=4) },                         # existing + gossip lines
  "reflections": { name: "" },                                  # Smallville-lite, §4.4
}
```

---

## 3. The reaction pipeline V2 (`agents.py` — extend, keep mock mode)

`react(world_id, event, mode="solo") -> ReactionResult` where ReactionResult carries:
`reactions[]` (name, mood, text, model, drama, moved_to|None, vibe_delta, affinity_deltas),
plus `gossip` (optional spread line), `consequence` (optional follow-up beat), `town_mood_delta`.

Per character each turn:
1. reroll mood; gather memory (incl. any gossip injected last turn) + reflection + relationships + vibes.
2. build prompt (existing template) + a **movement hint** ("if you'd go somewhere, end with [GOTO: cafe]")
   and a **surprise seed**. Parse `[GOTO: x]` → `moved_to` hotspot; strip it from displayed text.
3. generate (concurrent, ThreadPool). Update memory. Compute `drama`, `vibe_delta`, `affinity_deltas`
   (simple heuristics: stress words ↓energy; helping a relation ↑affinity; etc. — mock: random small).
After all 5: apply deltas to world-state, update town_mood, maybe spawn gossip & consequence (§4).

Keep **all of this mock-testable** (`TINYWORLD_MOCK=1`) with canned varied output.

---

## 4. Storytelling systems (innovation, low complexity — this is the magic)

1. **Gossip ripple** (§ Smallville's information diffusion): after reactions, with prob ~0.5 pick the most
   dramatic reaction and inject `"You heard {name} just said: '{snippet}'"` into ONE random other
   character's memory → influences their NEXT turn. Log it in Town Log as a 🗣️ gossip line.
2. **Relationship & vibe drift**: apply `vibe_delta`/`affinity_deltas` to world-state; the Roster meters
   and relationship-web visibly move. Compounding discovery → "the town is changing because of me."
3. **Town Mood = weather**: aggregate of vibes; tints the stage (sunny ↔ stormy overlay) and biases prompts
   ("the town feels tense lately"). Makes the "you change the weather" metaphor literal & visible.
4. **Reflections (Smallville-lite)**: every 5 events, each character forms a 1-line reflection (1 cheap LLM
   call or mock) stored in state and injected into future prompts.
5. **Consequence beats**: with prob ~0.3 after an event, auto-generate a short follow-up referencing prior
   drama (e.g. "Because Jay tried to impress Nia, Marta now…") shown as a ⚡ beat in the Town Log.
6. **Chaos meter + Day counter**: each event +chaos & +event_count; every N events → Day++; chaos unlocks
   bigger 🎲 chaos events and a louder screen-shake. Gives a goal to chase.

---

## 5. The three modes (console behavior)

### 5.1 🎮 Solo (default sandbox)
Type/speak an event → ⚡Throw → 5 concurrent reactions on the stage + Town Log + auto-voice the most
dramatic + 👤hear any other. 🎲Chaos throws a world-flavored chaos event.

### 5.2 👥 Party (lean pass-and-play, multiplayer)
- **Setup:** pick player count (2–4), enter names.
- **Round:** the "host" types an event (others look away — a "🙈 Hide" button blanks the screen until ready).
- **Bet:** each player picks which resident will be **{rotating prompt}** — most dramatic / funniest /
  most selfish / most helpful / most surprising (rotates each round).
- **Reveal:** generate reactions → stage + voice. Players **vote** the winner → award points.
- **Scoreboard** persists across rounds (gr.State); after N rounds → 🏆 leaderboard.
- No websockets — single screen, sequential. Keep round manager minimal.

### 5.3 🎓 Learn (full — classroom/teacher angle)
- **Scenario picker** per world (each scenario = title + an event string + a teaching focus), e.g.
  Greenfield School world: "The school will be closed by the city", "A new immigrant student joins",
  "The class pet goes missing".
- Run reactions as usual, THEN a **"🧠 Why did they react this way?"** button → one LLM call summarizing
  how each character's personality/backstory/relationships/mood shaped their reaction, in plain language.
- Show a **discussion prompt** ("Why did Nia focus on safety? Who would you have been?") for classroom use.
- Keep mock fallback for the explainer.

---

## 6. Visual system — FLUX diorama stage (the "realistic game" look)

### 6.1 Stage render (`render_stage(world, reactions, state)` → HTML)
Layered structure inside `gr.HTML`:
```html
<div class="stage" style="--tint: <town-mood/day-night>">
  <img class="stage-bg" src="assets/worlds/maple_street.png">      <!-- the FLUX diorama -->
  <div class="stage-overlay tint"></div>                            <!-- mood/day-night tint -->
  <!-- per character: positioned at hotspot %, with ground shadow + idle bob -->
  <div class="avatar" style="left:70%;top:40%" data-name="Nia">
     <div class="ground-shadow"></div>
     <div class="ring active"></div>                                <!-- when speaking -->
     <span class="avatar-emoji">🚑</span>
     <div class="mood">😊</div>
     <div class="bubble typewriter">…reaction text…</div>
  </div>
  <div class="shockwave"></div>                                     <!-- triggered on throw -->
</div>
```
- Avatars **slide** between hotspots via CSS `transition: left/top .8s` when `moved_to` changes.
- Bubbles spring-in **staggered** (50ms apart) + **typewriter** reveal; auto-dismiss ~7s (map.js).
- **Active-speaker ring** glows under whoever's voice is auto-playing.
- Stage tint shifts with town_mood (warm→cold) and a slow day/night cycle.

### 6.2 FLUX art pipeline (`tools/generate_art.py`) — adds **Black Forest Labs** sponsor
Generate each world's diorama ONCE with **FLUX.2-klein**, save PNG, ship it (committed). Runtime never
loads FLUX → runtime models stay ≤4B (Tiny Titan safe); FLUX is a build-time art tool (credit BFL in README).

Prompt template per world:
```
"isometric diorama of a {theme}, cute stylized low-poly game art, soft warm lighting,
 clean empty streets (no characters), top-down 3/4 view, vibrant cohesive palette,
 game asset, high detail, centered, plain sky" , size ~1024x768
```
Optional stretch: generate 5 character **portrait chips** per world (for roster cards & bubbles) the same way.
If FLUX access is unavailable in time → fallback to **Kenney CC0 isometric art** assembled into a backdrop,
OR the isometric-CSS map; the stage code reads a PNG either way, so this is swappable.

---

## 7. The Worlds (playgrounds) — author these as data (§2)

Ship **5 worlds** (start with #1 working end-to-end, then clone the pattern):
1. **Maple Street** — cozy modern suburb (existing cast: Marta, Jay, Nia, Luca, Priya). *Default.*
2. **Old Town Market** — bustling market square (vendor, tourist, busker, pickpocket-with-heart, grandma).
3. **Starhaven Station** — sci-fi space colony (the "futuristic" vibe: engineer, android barista, captain, stowaway kid, botanist).
4. **Mistwood Hollow** — cozy fantasy hamlet (witch, blacksmith, talking cat, lost knight, herbalist).
5. **Greenfield School** — a school (teacher + 4 students) — anchors the Learn-mode classroom story.

Each world = diorama PNG + 5 characters (3 MiniCPM5-1B / 2 Nemotron-3-Nano-4B) + hotspots + 6 themed
events + 4 learn scenarios. **This is mostly data** — high content value, low code risk.

---

## 8. Execution phases & TODOs (for Codex/opencode — build in order, test each)

> Rules every phase: keep `TINYWORLD_MOCK=1` working on CPU; degrade gracefully; update `CHECKPOINT.md`;
> **do not commit unless you are Codex** (others leave work uncommitted for Codex to commit).

### Phase A — Foundation refactor (data-driven worlds)
- [ ] Create `worlds/` package + `WORLDS` registry; move current 5 chars into `worlds/maple_street.py` cast.
- [ ] Add new character fields (emoji, home, catchphrase_hint) + world hotspots/scenarios/events.
- [ ] Add `world_state.py` runtime state (day/chaos/town_mood/vibes/affinity/memory/reflections) with reset-on-switch.
- [ ] Refactor `agents.react()` → `react(world_id, event, mode)`; parse `[GOTO: x]`; compute drama/deltas; keep mock.
- [ ] Test: `TINYWORLD_MOCK=1` react on maple_street → 5 reactions with moods, deltas, optional [GOTO]; runs twice differently.

### Phase B — Stage redesign (the new look & layout)
- [ ] Implement `render_stage()` (layered diorama + avatars at hotspots + bubbles + rings + shockwave).
- [ ] Rebuild `app.py` layout to the §1 HUD (top bar, roster rail, stage, town log, docked console, mode tabs).
- [ ] Roster cards with mood + 2 animated vibe meters; top status ticker (Day/events/chaos); World picker.
- [ ] `style.css` + `map.js`: avatar slide, staggered+typewriter bubbles, shockwave, active ring, tint.
- [ ] Test: `TINYWORLD_MOCK=1 python3 app.py` → throw event → avatars react on the diorama, meters move, log fills, no traceback.

### Phase C — Juice pass
- [ ] Map shockwave + subtle screen-shake on Throw (bigger on Chaos); SFX optional (CC0 wavs).
- [ ] Meter-tick animations; button squish/hover-pulse; day/night + town-mood tint drift; idle avatar bob.

### Phase D — Storytelling systems
- [ ] Gossip ripple · relationship/vibe drift · town-mood weather · reflections (every 5) · consequence beats · chaos meter/day counter (§4). All mock-safe.
- [ ] Relationship-web overlay toggle on the stage.
- [ ] Test: after ~6 events, meters & affinities have visibly changed; a gossip line and a consequence beat have appeared.

### Phase E — Modes
- [ ] 👥 Party mode (setup → hide → bet → reveal → vote → scoreboard → leaderboard), gr.State only.
- [ ] 🎓 Learn mode (scenario picker + "Why did they react?" explainer + discussion prompt), mock fallback.

### Phase F — Content (worlds + art)
- [ ] `tools/generate_art.py` (FLUX.2-klein) → diorama PNGs for all worlds; commit PNGs; credit BFL.
- [ ] Author worlds #2–#5 as data (cast + hotspots + events + scenarios).
- [ ] Test: switch worlds → diorama, cast, hotspots, scenarios all swap correctly.

### Phase G — Sponsor & submission
- [ ] README: hook blurb, how-to-play (3 modes), **model param table proving ≤32B** (MiniCPM5-1B 1B +
      Nemotron-3-Nano-4B 4B + VoxCPM2 2B + Cohere Transcribe 2B; FLUX.2-klein = build-time art, BFL),
      Modal parallel-latency note, GitHub link, demo video. Frontmatter tags.
- [ ] UI footer credits all sponsors (OpenBMB, NVIDIA, Cohere, Modal, Black Forest Labs, OpenAI Codex).
- [ ] Secrets as Space secrets (COHERE_API_KEY, Modal token). Deploy under `build-small-hackathon` org.
- [ ] Record 60–90s demo of the magic moment; post for Community Choice.
- [ ] **Codex commits** all outstanding work in logical steps with `Co-authored-by: Codex <codex@openai.com>`.

---

## 9. Priority & guardrails
- **Order:** A → B (this gets a far better-looking, working app — re-submit here) → D → C → E → F → G.
  Party/Learn (E) and extra worlds (F) are the "more chances to win" content the owner asked for; do them
  after the core stage + storytelling feel great.
- Every new system must be **mock-testable** and **degrade gracefully**; never block the demo path.
- Content (worlds, scenarios) is cheap & high-value — lean into it once the engine is solid.
- Keep ONE LLM call per character — resist mAIndlock-style multi-LLM cascades (complexity we don't need).
- Sponsor compliance is non-negotiable: runtime models ≤4B, FLUX only at build-time, all credited.
