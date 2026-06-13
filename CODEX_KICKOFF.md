# Codex kickoff prompt — paste the block below into Codex

Run `codex` inside `/home/laptop/App_development/tiny_word`, then paste everything between the lines.

---------------------------------------------------------------------------------------------------

You are building **TinyWorld** for the Build Small Hackathon. Your single source of truth is
`AGENTS.md` in this repo — read it in full before writing any code, and follow it over the older
brief docs where they disagree (the brief has API errors that AGENTS.md corrects).

## Your objective
Build the **Phase-1 MVP only** (the section "MVP scope" in AGENTS.md). Do NOT build any deferred
feature (no map builder, no character creator, no multiplayer, no learning mode, no day/night) until
the MVP demos cleanly. Phase 2 (Modal) comes later — not now.

## Work in this exact order, and TEST each step before the next
Follow the "File structure & build order" in AGENTS.md:
1. `characters.py` + `unpredictability.py`
2. `agents.py` (5 concurrent reactions)
3. `app.py` skeleton (map HTML + event input + feed; mock voice)
4. `voice.py` (auto-voice + click-to-hear)
5. `assets/style.css` + `assets/map.js`
6. `transcribe.py`
7. `events.py`
8. `requirements.txt`
9. `README.md`

After finishing each numbered step, RUN its test command from the "Run / test commands" section in
mock mode (`TINYWORLD_MOCK=1`) and confirm it passes. **Do not move to the next step while the current
one fails or is untested.** This is the rule that prevents bugs from piling up. If a test fails, fix it
before continuing.

## Hard rules you must not break
- Use ONLY the models and APIs exactly as pinned in AGENTS.md (MiniCPM5-1B, NVIDIA-Nemotron-3-Nano-4B,
  VoxCPM2 inline-parenthesis API, Cohere `cohere-transcribe-03-2026`). Every model ≤4B. Sponsor models only.
- Before writing `transcribe.py`, open https://docs.cohere.com/v2/docs/transcribe and its API reference
  and copy the REAL client+method — do not guess. If unsure, wrap in try/except and fall back to text input.
- Implement the **`TINYWORLD_MOCK=1`** mode in every model module (see AGENTS.md "Mock mode") so the app
  is fully testable on CPU. Build and verify everything in mock mode first.
- The app must never hard-fail the demo path: transcription or voice errors degrade gracefully.
- No secrets in code. `COHERE_API_KEY` comes from the environment.

## Checkpointing (so work survives your 5-hour limit)
Maintain `CHECKPOINT.md` at the repo root per the "Checkpoint & resume protocol" in AGENTS.md. Update
it after EVERY completed step (Done & verified / In progress / Next up / Blockers / How to resume). This
lets another agent or a fresh session continue exactly where you left off if you run out of time.

## Commits (this is how the OpenAI Codex prize is won — do it carefully)
- Commit after each working+tested step. Small, labeled commits. Never squash.
- Every commit message ends with the trailer: `Co-authored-by: Codex <codex@openai.com>`
- Commit `CHECKPOINT.md` together with each step's code.
- ALL commits go through you (Codex) only. If a different agent helped while you were paused, review
  their uncommitted changes, run the tests, and commit them yourself.

## Acceptance check before you call the MVP done
Run the "demo moment" test from AGENTS.md three times: trigger
"A mysterious glowing object lands in the park" → 5 distinct in-character bubbles appear fast, one
auto-speaks, the feed logs all 5, and reactions differ across the three runs (proving the 4-layer
unpredictability works). When this passes in mock mode, report what real-model validation on the Space
still needs.

Start now: read AGENTS.md, create `CHECKPOINT.md`, then begin step 1.

---------------------------------------------------------------------------------------------------
