# CHECKPOINT

## Done & verified
- Step 1 — `characters.py` (5 characters) and `unpredictability.py` (moods, seeds, memory, relationships). Pre-existing, verified.
- Step 2 — `agents.py` — Real Modal inference via HTTP endpoints. Batch approach sends all characters per model in one request. Mock mode still works with `TINYWORLD_MOCK=1`. Tested: 5/5 characters get real responses from MiniCPM5-1B on Modal.
- Step 3 — `events.py` — 12 chaos events + `random_event()`. Verified.
- Step 4 — `voice.py` — Real VoxCPM2 via Modal endpoint. Tested: returns 307KB WAV. Mock mode still works.
- Step 5 — `transcribe.py` — Cohere Transcribe with mock fallback. Verified.
- Step 6 — `app.py` — Gradio 6.x Blocks with server-rendered pixel map, speech bubbles, feed, event input, voice playback. Fixed: `css`/`js` moved to `launch()` per Gradio 6.x API. Fixed: `gr.Dropdown(...)` return instead of `gr.update()`. Live on http://127.0.0.1:7860.
- Step 7 — `assets/style.css` (822 lines) — Full design system with shockwave, screen-shake, typewriter, roster HUD, chaos meter, recap card, responsive breakpoints (900px + 600px).
- Step 8 — `assets/map.js` — Auto-dismiss bubbles, shockwave rings, screen-shake, staggered bubbles (80ms), typewriter reveal, idle overlay hide on trigger.
- Step 9 — `requirements.txt` + `README.md`.
- Modal deployment — `modal_app.py` deployed to Modal (`ap-d5n4oAb6rXIRRlxOB8H8dp`). Endpoints:
  - LLM: `https://mitvho09--tinyworld-inference-react-endpoint.modal.run`
  - Voice: `https://mitvho09--tinyworld-inference-voice-endpoint.modal.run`
  - All using `openbmb/MiniCPM5-1B` on A10G GPU.
- 🔴 Immediate features (ALL DONE):
  - Map shockwave rings on trigger + 180ms screen-shake
  - Staggered bubble spring-in (80ms apart) + typewriter reveal
  - Character roster HUD: 5 portrait cards with mood emoji + animated vibe bars (energy/social)
  - Vibe drift: moods nudge energy/social values after each event
  - Verified "I didn't expect that" bar: 3x same event → unique reactions
- 🟠 Important features (ALL DONE):
  - Consequence chain: 40% chance of follow-up beat referencing a prior reaction
  - Chaos meter + progression ticker: "Day N · events · chaos ▮▮▮▯▯"
  - Recap card: "📸 TODAY IN TINYWORLD" with top 3 dramatic reactions
- 🟡 Stretch features:
  - Smallville-lite reflections: every ~5 events, each character forms a one-line reflection injected into prompts
- 🟢 Juice polish:
  - Active-speaker glow ring + pulse animation
  - Meter-tick flash animation on vibe changes
  - Idle overlay: "The neighborhood is quiet..." with breathing animation
  - Button squish on press
  - Loading state overlay
  - Mobile responsive: 900px + 600px breakpoints with roster/bubble/ticker scaling

## In progress
- Repo publication — public GitHub repo is being created and the README source link is being wired to it.

## Next up
- Commit the current workspace and push it to the new public repo.
- Verify Codex attribution in git history.

## Blockers / decisions
- Nemotron removed — `mamba-ssm` won't build on Modal. All 5 chars use MiniCPM5-1B (still sponsor model, ≤4B).
- Gradio 6.18.0 installed locally. HF Space may use different version.
- `COHERE_API_KEY` needed for real transcription (not tested without key).
- Some mock reactions duplicate on 3x repeat (finite canned pool). Real LLM fully unique.

## How to resume
- Read `AGENTS.md`, then this file. Run `TINYWORLD_MOCK=1 python3 app.py` to test locally. All Modal endpoints deployed. All features built and smoke-tested. Ready for Codex to review & commit.
