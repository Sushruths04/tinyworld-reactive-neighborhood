# TinyWorld — Detailed Build Guide (for the opencode / MiMo session)

This is the **concrete, step-by-step spec** for finishing TinyWorld. Read it together with `AGENTS.md`
(hard rules + exact model APIs) and `CHECKPOINT.md` (current state). Where this guide shows code, treat
it as the intended shape — match the signatures and structure exactly; you may improve the bodies.

> **You are not starting from zero.** Codex already built and verified the "brain" layer:
> `characters.py` (5 characters) and `unpredictability.py` (moods, 10 surprise seeds, 3-event memory,
> relationship formatter). DO NOT rewrite those. Build on top of them.

---

## 0. Working rules (read before touching anything)

1. **Mock-first.** Every model module must honor `TINYWORLD_MOCK=1` (env var) and return canned output
   with NO model download/load. Build and test the entire app in mock mode on CPU. Real models only run
   on the Hugging Face Space (GPU). This is non-negotiable — it is how we test without a GPU.
2. **Test each step before the next.** After each file, run its smoke test (given per step). Do not stack
   unverified modules.
3. **DO NOT git commit. DO NOT run git at all.** All commits are reserved for Codex (for the OpenAI Codex
   prize). You only write/edit files and update `CHECKPOINT.md`. Codex will commit your work when its
   limit resets.
4. **Update `CHECKPOINT.md` after every step** (Done & verified / In progress / Next up / Blockers /
   How to resume) so any agent can pick up cleanly.
5. **Never break the demo path.** If transcription or voice fails, the app must still work via text.
   Wrap every external/model call in try/except with a graceful fallback.
6. **Sponsor models only, every model ≤4B.** Do not add or swap models. The pinned ids and APIs are in
   `AGENTS.md` — follow them exactly (especially: VoxCPM2 voice description is INLINE in the text in
   parentheses; Cohere method must be read from live docs).

---

## 1. The aesthetic: "Cozy-Future Pixel Art" (this is what makes it not look basic)

We want judges to feel *"this is a polished little game,"* not *"this is a default Gradio form."*
The look = **charming 16-bit pixel neighborhood** sitting inside a **premium dark, glowing, animated
UI shell**. Retro tiles + modern chrome.

**Design tokens (use these exact values):**

```
/* Surfaces */
--bg-0:        #0b0f1a;   /* app background, near-black navy */
--bg-1:        #121829;   /* panels */
--bg-2:        #1b2235;   /* raised cards */
--glass:       rgba(20,28,48,0.55);  /* glassmorphism panels (with backdrop-filter: blur(12px)) */
--stroke:      rgba(120,160,255,0.18);

/* Neon accents (glow) */
--neon-cyan:   #38e8ff;
--neon-violet: #9b6bff;
--neon-pink:   #ff5fa2;
--neon-lime:   #7CFFB2;
--gold:        #ffd76a;

/* Pixel-world palette (the map tiles only) */
--grass: #5a8a3c;  --road: #6f7790;  --sky: #87ceeb;  --beige: #f5deb3;
--water: #3aa0c8;  --roof: #c45b5b;  --tree: #2f7d46;

/* Text */
--text:   #eaf0ff;
--muted:  #93a0c2;
```

**Type:** `Press Start 2P` for the logo/section titles (tiny, used sparingly — it's heavy), `VT323`
for speech bubbles and the feed, and a clean sans (`Inter`, system fallback) for body/controls. Load
fonts via a `<link>` injected in `gr.HTML` (Google Fonts).

**Signature touches (these read as "futuristic/premium"):**
- Glassmorphism side panels (`backdrop-filter: blur(12px)`, 1px `--stroke` border, soft inset).
- Neon glow on the title and active buttons (`text-shadow`/`box-shadow` with the accent color).
- A subtle animated starfield/aurora gradient behind the map (slow CSS keyframe drift).
- An **event ripple**: when an event triggers, a cyan ring expands across the map (`@keyframes ripple`).
- Speech bubbles **spring in** (`@keyframes bubble-in`, scale 0→1.05→1) and gently float.
- Mood emoji above each character **bounces** (`@keyframes mood-bounce`).
- A "thinking" state: while reactions generate, characters get a pulsing `…` bubble + a top progress shimmer.
- Smooth everything: `transition: all .25s cubic-bezier(.2,.8,.2,1)` on interactive elements.

Keep tiles crisp pixel art: `image-rendering: pixelated;` and chunky flat colors, NO gradients on tiles
(gradients only on the background/chrome).

---

## 2. Build order & per-file specs

Build steps 2→9. Test in mock mode after each.

### Step 2 — `agents.py`  (the reaction engine)

Imports `characters` and `unpredictability`. Public API:

```python
def build_agent_prompt(character, event, mood, memory, relationships) -> str
def react(event: str) -> list[dict]      # one dict per character, generated CONCURRENTLY
```

Each reaction dict: `{"name", "job", "mood", "model", "text", "drama": float}`.
- Run the 5 characters concurrently with `concurrent.futures.ThreadPoolExecutor(max_workers=5)`.
- For each character: `mood = unpredictability.reroll_mood(name)`, `memory = get_recent_memories(name)`,
  `relationships = format_relationships(char)`, then build the prompt and generate text.
- After generating, call `unpredictability.update_memory(name, event, text)`.
- `drama` = a heuristic score (0–1) used to pick which reaction auto-plays as voice. Mock: random;
  real: e.g. length + count of "!"/caps words. The app auto-voices `max(drama)`.

**Prompt template** (use AGENTS.md's; 2–3 sentences, in-character, reference mood/memory/relationships,
append one random surprise seed, "DO NOT be predictable, NO narration").

**Real model loading (only when NOT mock):** lazy-load each family once into module globals behind a
`@spaces.GPU` function. `openbmb/MiniCPM5-1B` and `nvidia/NVIDIA-Nemotron-3-Nano-4B` via
`transformers` (`AutoModelForCausalLM`+`AutoTokenizer`, `trust_remote_code=True`, `device_map="auto"`,
`torch_dtype="auto"`). Build inputs with `tokenizer.apply_chat_template([{role:"user",content:prompt}],
add_generation_prompt=True, return_tensors="pt")`. Generate with `max_new_tokens=120, do_sample=True,
temperature=0.9, top_p=0.95`. Decode only the new tokens. Group characters by model so each model loads once.

**Mock mode:** return varied canned reactions built from the character's traits + current mood + chosen
surprise seed, so output visibly differs every run. Keep them short and funny/in-character.

**Smoke test:**
```
TINYWORLD_MOCK=1 python3 -c "import agents; [print(r['name'], '|', r['mood'], '|', r['text']) for r in agents.react('A mysterious glowing object lands in the park')]"
```
Pass = 5 distinct in-character lines; run twice → lines change.

### Step 3 — `events.py`

`CHAOS_EVENTS = [...]` — use the 12 from the brief (food truck free pizza, glowing object lands, mayor
closes shops, someone wins the lottery, viral video spot, water cut 24h, celebrity moving in, WFH law,
free concert tonight, strange smell from abandoned building, snow in 2h, mystery new neighbor).
Add `def random_event() -> str`.

### Step 4 — `voice.py`

```python
def build_voice_description(character) -> str   # returns the inline parenthetical, e.g. "(a grumpy elderly woman, deep low voice)"
def generate_voice(text: str, voice_desc: str) -> str   # returns path to a wav file
```
- Real: `from voxcpm import VoxCPM`; lazy-load `VoxCPM.from_pretrained("openbmb/VoxCPM2")` once;
  `wav = model.generate(text=f"{voice_desc}{text}", cfg_value=2.0, inference_timesteps=10)`;
  `soundfile.write(path, wav, model.tts_model.sample_rate)`; return path. Wrap in `@spaces.GPU`.
- Mock: write ~0.4s of silence to a temp wav and return its path.
- Characters already carry `voice_description`, so `build_voice_description` can just return that field.

**Smoke test:** `TINYWORLD_MOCK=1 python3 -c "import voice,characters as c; print(voice.generate_voice('Hi!', c.CHARACTERS[0]['voice_description']))"` → prints a wav path that exists.

### Step 5 — `transcribe.py`

```python
def transcribe(audio_path: str | None) -> str   # mic audio -> text; "" on failure
```
- **Before writing:** open https://docs.cohere.com/v2/docs/transcribe + its API reference and copy the
  REAL client+method. Use `cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])`, model
  `"cohere-transcribe-03-2026"`, audio ≤25MB.
- Mock OR missing key OR any exception → return a fixed sample like
  `"A street parade just showed up out of nowhere."` and never raise.

### Step 6 — `app.py`  (Gradio Blocks — the orchestration)

This is the highest-risk file; follow this structure closely.

**Map rendering is SERVER-SIDE** (return an HTML string each update — simplest & most reliable). The map
is a fixed 12×8 CSS grid; characters are emoji on fixed home tiles; speech bubbles are rendered into the
same HTML when reactions exist.

```python
import gradio as gr
import agents, voice, transcribe, events, characters as chars
from unpredictability import get_mood

EMOJI = {"Marta Voss":"🧓","Jay Park":"🚴","Nia Okafor":"🚑","Luca Bell":"🧒","Priya Raman":"👩‍💼"}
HOME  = {"Marta Voss":(1,1),"Jay Park":(3,9),"Nia Okafor":(5,2),"Luca Bell":(2,6),"Priya Raman":(6,7)}  # (row,col) on the 8x12 grid

def render_map(reactions=None) -> str:
    # build a <div class="tw-map"> with 96 tiles (pre-painted: grass/road/park/houses),
    # then place each character emoji + mood bubble at HOME[name];
    # if reactions given, add a .bubble with the character's text (VT323) above their tile.
    ...

def trigger(event_text):
    reactions = agents.react(event_text)              # 5 concurrent
    top = max(reactions, key=lambda r: r["drama"])    # auto-voice the most dramatic
    audio = voice.generate_voice(top["text"], next(c["voice_description"] for c in chars.CHARACTERS if c["name"]==top["name"]))
    feed_lines = [f'{EMOJI[r["name"]]} {r["name"]} ({r["mood"]}): "{r["text"]}"' for r in reactions]
    return render_map(reactions), "\n".join(feed_lines), audio, gr.update(choices=[r["name"] for r in reactions])

def hear(name, event_text_state, last_reactions_state):
    # play a chosen character's last reaction on demand
    ...
```

**Layout (gr.Blocks, custom theme + css=open("assets/style.css").read()):**
- Top bar: 🏘️ **TINYWORLD** logo (neon), tagline, and a small "Models: MiniCPM5-1B · Nemotron-3-Nano-4B · VoxCPM2 · Cohere Transcribe" credit strip.
- Main row (2 columns):
  - **Left (≈65%)**: `gr.HTML(render_map())` — the living map, inside a glass panel with the animated aurora background behind it.
  - **Right (≈35%)**: glass panel "📜 NEIGHBORHOOD FEED" = `gr.Markdown`/`gr.HTML` scrolling log.
- Event bar (below map): `gr.Textbox(placeholder="Throw an event at the neighborhood…")` +
  `gr.Audio(sources=["microphone"], type="filepath")` (→ on stop, call `transcribe` to fill the textbox) +
  **⚡ Trigger** button + **🎲 Random Chaos** button (fills textbox via `events.random_event`).
- Voice row: `gr.Audio(autoplay=True)` for the auto-played dramatic reaction + a `gr.Dropdown` of the 5
  names + **🔊 Hear this one** button (calls `hear`).
- Footer: full sponsor credit line + "Built for Build Small Hackathon 2026 · Thousand Token Wood".

Use `gr.State` to hold the last `reactions` list and last `event_text` for the `hear` handler.
Show a "neighborhood is waking up…" loading state on first GPU load (real mode).

**Smoke test:** `TINYWORLD_MOCK=1 python3 app.py` → opens locally; typing an event + Trigger shows 5
bubbles on the map, fills the feed, and plays (silent mock) audio. No traceback in console.

### Step 7 — `assets/style.css`

Implement the full design system from §1. Required keyframes: `ripple`, `bubble-in`, `mood-bounce`,
`aurora` (slow background drift), `shimmer` (loading bar). Glass panels, neon buttons (default + hover +
active glow), pixel tiles (`image-rendering:pixelated`), responsive (stack columns < 900px). Map grid:
`display:grid; grid-template-columns:repeat(12,1fr); grid-template-rows:repeat(8,1fr); gap:2px;`.
Bubbles: absolutely positioned over the map cell, `VT323`, white rounded rect with a little tail,
`animation: bubble-in .35s` then auto-fade after ~6s (CSS or set via JS).

### Step 8 — `assets/map.js` (small, optional)

Only if needed: auto-dismiss bubbles after a timeout and trigger the ripple element on trigger. Keep the
map itself server-rendered; JS is just polish. If time is short, do bubble fade purely in CSS and skip JS.

### Step 9 — `requirements.txt` + `README.md`

`requirements.txt`: `gradio>=5.0`, `spaces`, `transformers`, `torch`, `accelerate`, `voxcpm`, `cohere`,
`soundfile`, `numpy`, `sentencepiece`.

`README.md`: HF Space frontmatter (title, emoji 🏘️, `sdk: gradio`, `app_file: app.py`, colorFrom/To,
tags: track + sponsor model ids), the hook blurb (from the brief's README), how-to-play (3 steps),
**Models Used** with param counts proving ≤32B (MiniCPM5-1B 1B + Nemotron-3-Nano-4B 4B + VoxCPM2 2B +
Cohere Transcribe 2B = ~9B), the GitHub repo link, and a demo line.

---

## 3. How this will be evaluated (build to pass these)

**The 2-minute demo moment (most important):** fresh load → type *"A mysterious glowing object lands in
the park"* → within ~5s, 5 distinct speech bubbles spring up on the map, one auto-speaks in a fitting
voice, the feed logs all five with mood emoji, and at least one reaction makes you laugh or say "I didn't
expect that." Trigger it **3 times** → reactions differ each time (proves the 4-layer unpredictability).

**Scoring rubric (self-check before declaring done):**
- [ ] **Core magic** — reactions are surprising, in-character, and vary across runs. (40%)
- [ ] **Polish/UI** — looks like a premium little game, not a form: glass panels, neon, animated map, spring bubbles. Earns the Custom-UI badge. (25%)
- [ ] **Performance** — text reactions ≤6s; voice doesn't block the screen (lazy/auto-one). (15%)
- [ ] **Robustness** — mic/voice failures degrade to text; no tracebacks in the demo. (10%)
- [ ] **Sponsor compliance** — all 4 sponsor models used + credited in UI & README; every model ≤4B. (10%)

**Quality bars for the next agent specifically:** concrete over clever. Match the signatures above.
Prefer server-side HTML rendering over fragile client JS. Keep functions small and wrapped in try/except.
Every step ends with its smoke test passing in mock mode.

---

## 4. When you stop

Leave the work **uncommitted**, update `CHECKPOINT.md` precisely (what's done & tested, what's mid-flight,
exact next step, any blocker like the Cohere method), and note "ready for Codex to review & commit."
Codex will commit everything with its `Co-authored-by: Codex <codex@openai.com>` trailer when its limit resets.
