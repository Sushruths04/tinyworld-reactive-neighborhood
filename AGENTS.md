# AGENTS.md — TinyWorld (Codex build instructions)

You (Codex) are building **TinyWorld** for the **Build Small Hackathon** (Hugging Face × Gradio,
June 2026), targeting the **Adventure in Thousand Token Wood** track. Ship a Gradio app on a
Hugging Face Space where the player throws an event at a tiny pixel-art neighborhood and **5 AI
characters react unpredictably, in their own voices**.

Read this whole file before writing code. The detailed rationale lives in
`build small hackathon strategy.md` and the original brief, but **THIS file is authoritative** —
where it disagrees with the brief, follow THIS file. The brief's code snippets contain API errors
(see "API rules" below); do not copy them blindly.

---

## Hard constraints (never violate)

- Every model used must be **≤ 32B params**. We deliberately use only **≤4B models** (earns the *Tiny Titan* badge). Do not add a larger model.
- **Sponsor models only** (list below). Do not substitute a non-sponsor model.
- Ships as a **Gradio app** runnable as a **Hugging Face Space** (must have `app.py` + `requirements.txt`).
- Never commit secrets. `COHERE_API_KEY` (and later a Modal token) come from env / Space secrets.
- The app must **never hard-fail on the demo path**: if transcription or voice errors, degrade gracefully (text still works).

---

## Model stack (USE EXACTLY THESE — corrected, verified June 2026)

| Role | Model id | Sponsor |
|---|---|---|
| Warm/creative agents (3 characters) | `openbmb/MiniCPM5-1B` | OpenBMB |
| Logical/structured agents (2 characters) | `nvidia/NVIDIA-Nemotron-3-Nano-4B` | NVIDIA |
| Character voices (TTS) | `openbmb/VoxCPM2` | OpenBMB |
| Speech → text (mic) | Cohere Transcribe, model `cohere-transcribe-03-2026` | Cohere |

One model instance per family serves multiple characters — do NOT load duplicate copies.
Load both LLMs + VoxCPM2 locally via the GPU; Cohere Transcribe is a hosted API call.

### API rules (the brief gets these WRONG — follow these instead)

**VoxCPM2** — the voice description goes *inline inside the text, in parentheses*. There is **no**
`voice_description=` or `speed=` kwarg.
```python
from voxcpm import VoxCPM            # pip install voxcpm
import soundfile as sf
_model = VoxCPM.from_pretrained("openbmb/VoxCPM2")
wav = _model.generate(
    text="(a grumpy elderly man, deep slow low-pitched voice)This reminds me of 1987.",
    cfg_value=2.0, inference_timesteps=10,
)
sf.write("out.wav", wav, _model.tts_model.sample_rate)   # 48 kHz
```
So `build_voice_description(character)` returns a parenthetical prefix string, and
`generate_voice(text, voice_desc)` does `_model.generate(text=f"{voice_desc}{text}", ...)`.

**Cohere Transcribe** — `co.transcribe(audio=...)` is almost certainly the wrong method.
**Before writing transcribe.py, open https://docs.cohere.com/v2/docs/transcribe and its linked API
reference, and copy the real client class + method.** Use `cohere.ClientV2(api_key=...)`, model
`"cohere-transcribe-03-2026"`, audio ≤25 MB. If you cannot confirm the method, wrap the call in
try/except and fall back to text-only input — never block the app.

**MiniCPM5-1B / Nemotron-3-Nano-4B** — load with `transformers` (`AutoModelForCausalLM` +
`AutoTokenizer`, `torch_dtype="auto"`, `device_map="auto"`, `trust_remote_code=True`). Build prompts
with each tokenizer's `apply_chat_template(..., add_generation_prompt=True)`. Generate with
`max_new_tokens≈120`, `temperature≈0.9`, `do_sample=True` (we WANT variety). Do not assume an HF
serverless provider hosts them.

---

## Phase 1 (BUILD THIS FIRST — hybrid) vs Phase 2 (after first submission)

- **Phase 1:** 2 LLMs + VoxCPM2 run locally behind a GPU; Cohere via API. Deploy to a HF Space (ZeroGPU). Gate GPU functions with `@spaces.GPU` and `import spaces`.
- **Phase 2 (must-do later, not now):** migrate ALL inference to **Modal serverless** (one function per model family, called in parallel), keeping the Space as a thin UI. Put this in `modal_app.py` behind a feature flag so Phase-1 still runs. Do NOT start Phase 2 until the MVP demo works end-to-end.

---

## MVP scope

**BUILD (must work flawlessly):**
1. **Fixed pre-built pixel-art neighborhood** — 12×8 CSS grid rendered via `gr.HTML`. No click-to-place builder.
2. **5 pre-made characters** (`characters.py`): name, age, job, 2–3 traits, 1-line backstory, relationships, a VoxCPM2 voice description, and a model assignment (3 → MiniCPM5-1B, 2 → Nemotron). Render each as a large emoji on its home tile with a mood emoji above it.
3. **Throw an event**: textbox + mic (Cohere Transcribe) + **⚡ Trigger** button + **🎲 Random Chaos Event** button (`events.py`).
4. **4-layer unpredictability system** (`unpredictability.py`) — see next section. This is the product; implement all 4.
5. On trigger: generate all 5 **text** reactions **concurrently** (threads / `concurrent.futures`) → show animated **speech bubbles** + append to a scrolling **Neighborhood Feed** (`name (mood emoji): reaction`).
6. **Voice**: auto-play only the single most-dramatic reaction via VoxCPM2; every other bubble is click-to-hear. (Avoids 15–20s of sequential TTS.)
7. **Sponsor credits** visible in the UI footer and README.

**DO NOT BUILD YET (deferred bonus):** click-to-place builder · in-app character creator · character
movement between tiles · multiplayer guessing · learning mode · day/night cycle · chaos-unlock-after-5.

---

## The 4-layer unpredictability system (`unpredictability.py`)

1. **Hidden mood** per character from `MOODS = ["happy","stressed","bored","excited","hungry","tired","nostalgic","curious","proud","embarrassed"]`; re-roll after every event.
2. **Short-term memory** = last 3 reactions per character, injected into the prompt.
3. **Relationship dynamics** (friend/rival/crush/family) injected into the prompt.
4. **Surprise seed** — one random instruction from `SURPRISE_SEEDS` (use the 10 from the brief) appended to every prompt.

Prompt template per character: persona (name/age/job/traits/backstory) + current mood + recent
memories + relationships + the event + "Respond in 2–3 sentences, stay in character, reference mood/
memory naturally, DO NOT be predictable, no narration — just your direct reaction."
Acceptance bar: trigger the same event 3× → reactions differ each time. If a reaction feels obvious,
the surprise seeds are too weak.

---

## File structure & build order

Build in this order, committing after each working step:
1. `characters.py` (5 characters + voice descriptions + model assignment) and `unpredictability.py` (moods, seeds, memory, relationship text).
2. `agents.py` — load both LLMs; `build_agent_prompt()`; `react(event) -> list[reaction]` running the 5 characters concurrently. Test standalone with a `print` before any UI.
3. `app.py` — Gradio `Blocks` skeleton: map HTML + event input + feed. Wire trigger → `react()` → bubbles + feed. (Mock voice first.)
4. `voice.py` — VoxCPM2 load + `generate_voice()`; wire auto-voice + click-to-hear into `app.py`.
5. `assets/style.css` + `assets/map.js` — pixel-art grid, character/emoji placement, `ripple`/`bubble-in`/`mood-bounce` keyframes. Palette: grass `#5a8a3c`, road `#8a8a8a`, sky `#87ceeb`, beige `#f5deb3`. Fonts "Press Start 2P" (title) + "VT323" (bubbles).
6. `transcribe.py` — Cohere mic→text with graceful fallback.
7. `events.py` — CHAOS_EVENTS list.
8. `requirements.txt` — `gradio`, `spaces`, `transformers`, `torch`, `accelerate`, `voxcpm`, `cohere`, `soundfile`, `numpy`.
9. `README.md` — HF Space frontmatter (sdk: gradio, track, sponsors, model ids), the hook blurb, how-to-play, models-used list with param counts proving ≤32B, and the GitHub repo link.

---

## Mock mode (REQUIRED — so the app is testable without a GPU)

The two LLMs + VoxCPM2 need a GPU and large downloads, which may not exist on the local dev machine.
So every model module must support an env flag **`TINYWORLD_MOCK=1`**:
- `agents.react()` returns canned-but-varied in-character reactions (still run the 4-layer logic so moods/seeds visibly change the text) — no model load.
- `voice.generate_voice()` returns a short silent/placeholder wav.
- `transcribe.transcribe()` returns a fixed sample sentence.

This lets the full UI + game logic be built and tested on CPU. Real models run on the Space (ZeroGPU)
and in Phase 2 on Modal. Build and verify everything in mock mode first, then validate real inference
on the Space. Never let a missing GPU block UI/logic progress.

## Run / test commands

```bash
TINYWORLD_MOCK=1 python -c "import agents; print(agents.react('A mysterious glowing object lands in the park'))"  # 5 distinct reactions
TINYWORLD_MOCK=1 python -c "import voice; voice.generate_voice('Hello there!', '(a cheerful young woman)')"        # writes a wav
TINYWORLD_MOCK=1 python app.py        # launches Gradio locally on CPU
# On the Space (real models): unset the flag.
```
After each module: run its test above and confirm it passes BEFORE moving to the next step. Do not
stack unverified modules — that is how bugs hide.

## Checkpoint & resume protocol (REQUIRED — survives the Codex 5h limit)

Maintain a file **`CHECKPOINT.md`** at the repo root and update it after EVERY completed step. This is
how another agent (or a fresh Codex session) resumes without re-deriving anything if you hit the 5-hour
limit or stop mid-task. Keep it to these sections, always current:

```
# CHECKPOINT
## Done & verified
- <step> — <how it was tested + result>
## In progress
- <the exact step you were on, the file, and what's half-finished>
## Next up
- <ordered remaining steps from the build order>
## Blockers / decisions
- <anything unresolved, e.g. exact Cohere method, GPU issues>
## How to resume
- <one-paragraph: read AGENTS.md, then this file, run the test command for the in-progress step>
```

**Resume rule for the Codex 5h limit:** if Codex stops, a local agent may CONTINUE the implementation
by reading `CHECKPOINT.md` and writing code — but **must NOT git-commit**. All commits go through Codex
only (to preserve Codex attribution for the prize). When Codex resumes, it reviews the uncommitted work,
runs the tests, and commits it. Always commit `CHECKPOINT.md` together with each step's code.

---

## Commit & attribution rules (REQUIRED — this is how the Codex prize is won)

- Make **frequent, small, well-labeled commits** through the Codex CLI as you complete each build step. The OpenAI Codex track requires Codex-attributed commits in a public GitHub repo.
- Add a trailer to each commit: `Co-authored-by: Codex <codex@openai.com>`.
- Do not squash the history — the commit trail is the evidence of Codex authorship.
- After the MVP runs locally, the repo will be pushed to GitHub (`Sushruths04`) and deployed to a Space under the `build-small-hackathon` org; ensure the README links the repo.
