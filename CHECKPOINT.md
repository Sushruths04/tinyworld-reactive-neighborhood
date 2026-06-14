# CHECKPOINT

## Done & verified
- Phase A.1 — Created `worlds/` package with `__init__.py` (WORLDS registry) + `worlds/maple_street.py` (WORLD dict with id, name, theme, diorama, palette, 8 hotspots, 5 cast members with emoji/home/catchphrase_hint, 4 scenarios, 10 events).
- Phase A.2 — Created `world_state.py` with mutable runtime state per world (day, event_count, chaos, town_mood, vibes, affinity, moods, memory deque, reflections, positions) + init_cast, reset_world, apply_vibe_delta, apply_affinity_delta, maybe_form_reflection, get/set helpers.
- Phase A.3 — Rewrote `agents.py` to `react(world_id, event, mode)`. Now returns `{"reactions": [...], "town_mood_delta": ...}`. Each reaction has: name, mood, text, model, drama, moved_to, vibe_delta, affinity_deltas. Parses `[GOTO: hotspot]` from model output. Mock mode returns varied canned output with mood + surprise seed + occasional GOTO.
- Phase A.4 — Tested: `TINYWORLD_MOCK=1` react on maple_street → 5 distinct reactions, different across runs, goto parsing works, town mood delta computed.
- Phase B.1 — Built `render_stage(world_id, reactions)` → layered HTML with diorama background (or CSS gradient fallback), town-mood tint overlay, avatars at hotspot positions with ground shadows + idle bob + active-speaker rings + typewriter bubbles + shockwave.
- Phase B.2 — Rebuilt `app.py` to 3-zone game HUD: TOP BAR (logo + world picker + status ticker) · ROSTER RAIL (5 portrait cards with mood + vibe meters) · STAGE (diorama + avatars + bubbles) · TOWN LOG (scrolling feed) · DOCKED EVENT CONSOLE (textbox + mic + Throw + Chaos + Scenario dropdown) · voice row.
- Phase B.3 — Wrote new `assets/style.css` (neon-glass design system, stage, avatars, bubbles, shockwave, roster, ticker, log, console, responsive) + `assets/map.js` (staggered bubbles, typewriter reveal, auto-dismiss, shockwave trigger).
- Phase B.4 — Tested end-to-end: TINYWORLD_MOCK=1 → throw event → 5 avatars react on stage with bubbles, meters move, log fills, shockwave fires, voice plays. No traceback.

## Done & verified — UI REDESIGN V2.1 (futuristic isometric town, by Claude/Opus, 2026-06-14)
- Rebuilt `render_stage()` in `app.py`: real **CSS isometric town** (dusk sky + stars + moon, iso diamond-grid ground, diagonal roads, 6 extruded buildings with skewed roofs + neon roof glow + signs, trees, fountain) instead of the blank gradient + floating emoji. Characters are now **game pawns** (token disc + emoji + mood pip + name label + ground shadow + idle bob), depth-sorted by screen-y, that **walk between hotspots** (CSS left/top transition) and get a speaking ring + plumbob + speech bubble when reacting.
- Added `scenery` (buildings/roads/trees/props) + realigned `hotspots` to `worlds/maple_street.py` so pawns stand on plots in front of their buildings.
- Full **futuristic restyle** of `assets/style.css`: dropped unreadable pixel fonts (Press Start 2P / VT323) → **Orbitron** (display) + **Rajdhani/Inter** (body); full-bleed centered container (kills the black dead-zone on the right); compact roster cards w/ glowing vibe meters; big prominent event console (`#tw-console`); **Gradio default footer / "Use via API" / Settings hidden** via CSS.
- Fixed layout bugs: mic moved out of the top input row (no more overlap-on-type); larger stage (16:11); responsive breakpoints.
- `assets/map.js`: staggered bubble spring-in + typewriter, shockwave on throw, gentle idle wander; observer now watches the whole container (Gradio swaps gr.HTML nodes).
- Gradio 6.18 fixes: `css`/`js` passed to `launch()` (not Blocks ctor); removed invalid `show_api`; added `event_input.submit` (Enter to throw).
- **Mic root-cause:** browser blocks the microphone on `http://0.0.0.0:7860` (not a secure context). Fix = open **http://localhost:7860**; startup banner + in-app footer hint now say this. Transcription still degrades to mock/text if no key.
- Verified live (`TINYWORLD_MOCK=1 python3 app.py`): HTTP 200, new 18KB CSS served, `/do_trigger` via gradio_client → 5 speaking pawns + 5 bubbles + 6 log entries + roster/ticker update, no traceback.

## Done & verified — UI REDESIGN V3 (canvas game engine, by Claude/Opus, 2026-06-14)
Replaced the CSS-div "isometric" stage (looked like AI slop, characters teleported) with a real
**HTML5 canvas game** rendered in `assets/game.js` and verified by headless-Chrome screenshots.
- `assets/game.js`: full isometric renderer + requestAnimationFrame loop. Draws sky, iso tile ground (grass/road/plaza), **3D-shaded building cuboids** (left/right walls + roof + lit windows + roof sign), trees, depth-sorted painter's algorithm. Characters are pawn tokens (color disc + emoji + mood pip + name plate + shadow) with **steering physics** (accelerate → arrival ease → stop; no more jet-speed snapping), idle wander, walk-bob, speaking ring, plumbob, and on-canvas **speech bubbles with typewriter + word-wrap**. Shockwave ripple on event.
- Decoupled from Gradio's re-render: canvas is in a `gr.HTML` rendered ONCE; data flows through two hidden, off-screen `gr.Textbox`es — `#tw-world` (board+cast JSON, set once) and `#tw-reactions` (per-throw JSON, polled every 140ms by the engine). Both `interactive=True` so they render as real `<textarea>` (a non-interactive Textbox renders a `<div>` and breaks `.value` reads).
- `worlds/maple_street.py`: added a tile **`board`** (12×12 grid, road cols/rows, plaza, 6 buildings in tile coords, trees, `hotspots_tile`, `plaza_center`).
- `app.py`: `build_world_payload()` + `build_reactions_payload()` (maps `moved_to` hotspot → tile, else converge on plaza with jitter); `render_stage_shell()` = canvas + vignette; full-screen layout (container max-width 100%, stage `min(74vh,860px)`); 3-panel bottom row (Townsfolk / Town Log / Controls).
- **Voice fixed:** `voice.py` mock now synthesizes an audible per-line sine tone (was silent) so "🔊 Voice (most dramatic)" + "Hear character" are verifiable without GPU. Verified: peak amplitude 0.3, `/hear_reaction` returns audio, dropdown populates with all 5 names.
- **Mic fixed:** auto-transcribe on `mic_input.stop_recording` (no separate button needed); root cause of "no microphone found" is the non-secure `0.0.0.0` origin — must open **http://localhost:7860**; banner + footer say so.
- Logo: dropped `background-clip:text` (renders invisible in Chrome headless/some builds) → solid neon-cyan with glow.
- Verified live: `TINYWORLD_MOCK=1 python3 app.py` → HTTP 200, no traceback; headless screenshots show the town, idle pawns, and (with a seeded reaction) characters walking to the plaza with typewriter bubbles + speaking ring; `/do_trigger` reaction channel returns valid JSON (ts + 5 targets).

## Done & verified — V4 (bigger futuristic town · multi-map · Learn mode, by Claude/Opus, 2026-06-14)
- **Bigger map + futuristic buildings:** board is now 20×20 with a road grid (block layout) and a central
  park. `assets/game.js` renders 4 building kinds — `tower` (spire + pulsing beacon), `dome`, `glass`
  (glowing window bands), `block` (setback crown) — each with neon roof glow + a floating holo label
  (CLOCK TOWER, SKY OFFICE, CAFÉ…). Removed the ugly emoji-on-roof. Added animated **fountain** (water
  rings), **pond**, **benches**, **lamps** (light glow), **café patio**. Trees scattered in a park.
- **People spread out (no more center swarm):** each character has an in-character "haunt" + activity
  label in `board.activities` (e.g. Jay 🚴 races to the café on a bike (faster), Nia 🚑 to the clinic,
  Marta 🪑 park bench, Luca 🔎 fountain, Priya 🏢 office). `build_reactions_payload` sends a distinct
  target+activity+vehicle per character; pawns show the activity under their name. Verified: 5 distinct
  spread targets, no clustering.
- **Multiple maps:** added `worlds/starhaven.py` (sci-fi station) and `worlds/old_town.py` (historic
  market), each a full world (board + 5-character cast + scenarios + events). `worlds/__init__.py`
  registers all 3. `game.js` hot-swaps the scene when `#tw-world` changes, so the **World** dropdown now
  switches maps live (verified via `/switch_world`). Character colors are auto-assigned per world
  (`char_color` + PALETTE) so any cast gets distinct colors.
- **Learn / teaching mode:** new **🎓 Teaching scenario** picker + **Run Scenario** button (per-world
  scenarios). New **"Learn — Why did they react?"** panel (`render_explainer`) shows the scenario's
  focus question + one line per character tying their *mood* + *trait* + *catchphrase_hint* to their
  behavior — the educational hook ("teach kids how different people respond to the same situation").
- **Audio explained + voice input:** the three audio widgets now have caption text — 🎙️ Speak an event
  (record → fills box → THROW; auto-transcribes on stop), 🔊 Auto-voice (most dramatic reaction read
  aloud), 🎧 Hear a character (replay any character's last line). Mock voice is an audible tone.
- `agents.py`: added `GENERIC_MOCK` mood pool so new worlds' characters speak in-mood (not Marta's lines)
  when `TINYWORLD_MOCK=1`.
- `app.py`: `TW_DEFAULT_WORLD` env override (handy for testing a specific map).
- Verified by headless-Chrome screenshots (all 3 maps render distinctly; scenario run disperses people
  with bubbles + shockwave) and gradio_client (switch_world swaps cast + scenario list; run_scenario →
  5 distinct targets + explainer with focus + voice). HTTP 200, no tracebacks.

## Done & verified — V5 (living town · randomized life · voice auto-throw, by Claude/Opus, 2026-06-14)
- **Living, randomized town** (`assets/game.js`): added an **ambient crowd** (~12 pedestrians + dogs that
  follow random main characters) that continuously walk to random walkable tiles at varied speeds, plus
  **cars** cruising along every road line (reverse at edges). The 5 main characters now **roam the whole
  town** between events (55% pick a random named hotspot, else mill nearby) instead of hovering at home,
  and can "run" (speed boost). All depth-sorted with buildings/props.
- **Randomized event responses** (`build_reactions_payload`): each throw randomly picks a mode —
  `gather` (everyone converges on the square), `scatter` (spread across hotspots/edges), or `mixed`
  (in-character haunt vs random) — and a per-character `running` flag. Verified targets differ run-to-run.
- **Voice input fixed**: `mic_input.stop_recording → transcribe → .then(do_trigger)` so recording an
  event now **transcribes and throws automatically** (one action). Caption + footer state the mic only
  works on http://localhost (browsers block getUserMedia on 0.0.0.0 — that was the user's "can't input
  voice" issue). Mock transcribe returns text; mock voice is an audible tone.
- `build_world_payload` now also sends `hotspots` (for roaming) and `ambient` count.
- Verified: all 3 maps render with crowd + cars (headless screenshots); full feature pass via
  gradio_client — throw, random chaos, run scenario (+focus), hear character, transcribe, switch all 3
  worlds. HTTP 200, no tracebacks.

## Done & verified — V6 (real sprites · slower · readable UI · clear voice, by Claude/Opus, 2026-06-14)
- **Real sprites instead of emoji** (`assets/game.js`): `person()` draws a little human (animated
  legs/arms, torso in shirt color, skin head + hair) with a walk cycle; `dog()` a quadruped; `bike()`
  a cyclist with spoked wheels + frame + rider; `drawCar()` a proper car (body, cabin, windows, wheels,
  head/tail lights, direction-aware). Main characters are bigger people (sc 1.35) with name+activity
  tags + speaking ring + bubble; ambient crowd = pedestrians + a cyclist + dogs.
- **Slowed everything to a natural pace:** main walk maxV 0.85 (run 1.3, bike 1.9), ambient 0.5–1.4,
  cars 1.1–1.8 (were ~2.4–4.6). Walk/anim phase rates halved.
- **Realistic buildings:** `windowGrid()` lays a proper rows×cols of framed lit/unlit windows on both
  visible walls + a `door()` at the entrance; neon roof glow toned down (blur 14→7).
- **Voice UX clarified** (`app.py`): explicit **📝 Transcribe** button (record → Transcribe → text fills
  the event box with a ✅/⚠ status line → THROW). Removed the confusing auto-throw. Audio section retitled
  "🔊 Voice" with 3 clearly-labelled controls (record+transcribe · auto-voice · replay a character).
- **No more white/invisible widgets:** added force-dark CSS for all inputs, dropdown trigger + popup
  option list, audio players/controls, svelte blocks. Added a fixed **mic warning banner** (game.js)
  that appears when the page is opened on 0.0.0.0/non-secure origin, telling the user to use localhost.
- Scenarios: 3–4 per world (maple 4, starhaven 3, old_town 3).
- Verified: `node --check` clean, HTTP 200, headless screenshots show drawn people/cars/cyclists +
  window-grid buildings + dark UI; full gradio_client suite PASS (throw, transcribe button, run scenario
  + focus, hear voice, switch all 3 worlds, random chaos).

## Done & verified — V7 (juice pass · screen-shake · meter-glow · tint-drift, by Codex, 2026-06-14)
- **Screen-shake** on every event throw (`.stage.shake` keyframes, 0.5s).
- **Button squish + pulse glow** — active-state radial highlight tracks cursor, triple-pulse after throw.
- **Meter-tick glow** — vibe fills flash when width changes (MutationObserver watches `style.width`).
- **Day/night tint drift** — continuous 30s CSS gradient cycle on `.stage-tint`.
- **Mood pop** — character mood emoji pops + rotates when speaking starts.
- **Roster-card flash** — border-left flashes cyan on speak, fades back.
- **Log slide-in** — entries enter with elastic left-slide.
- **Title glow** — logo pulses neon glow on a 4s cycle.
- All juice in `assets/style.css` (9 new keyframe blocks, 574 total lines) + `assets/map.js` (146 lines).
- Verified: agents react, renders produce HTML, CSS/JS parse clean (balanced braces, all 8 class names present), app serves HTTP 200.

## Done & verified — V8 (Modal transcription + VoxCPM2 startup hardening, by Codex, 2026-06-14)
- Added a Modal ASR stack in `modal_app.py`: `asr_image` installs `ffmpeg` + `openai-whisper`; `ASR` loads Whisper `base`; `transcribe_endpoint` accepts raw audio bytes and returns `{"text": ...}`.
- Updated `transcribe.py` to call `MODAL_TRANSCRIBE_URL` first, then fall back to Cohere Transcribe when configured, then mock sample text if both real paths fail.
- Added `MODAL_TRANSCRIBE_URL` to `start.sh` and added local `httpx` to `requirements.txt`.
- Deployed Modal successfully. Current endpoints:
  - LLM: `https://mitvho09--tinyworld-inference-react-endpoint.modal.run`
  - Voice: `https://mitvho09--tinyworld-inference-voice-endpoint.modal.run`
  - Transcribe: `https://mitvho09--tinyworld-inference-transcribe-endpoint.modal.run`
- Verified Modal transcription endpoint server-side: cold-start loaded Whisper base, downloaded 139MB model, and returned `POST / -> 200 OK`.
- Hardened VoxCPM2 voice endpoint startup: `TTS` class timeout/startup_timeout increased to 900s and `voice.py` client timeout increased to 900s. Modal redeployed successfully with those settings.
- Local checks passed: `python3 -m py_compile modal_app.py transcribe.py voice.py app.py agents.py world_state.py worlds/*.py`, `TINYWORLD_MOCK=1` transcribe, `TINYWORLD_MOCK=1` `agents.react(...)`, `python3 validate_worlds.py`, and `node --check assets/game.js`.
- `TINYWORLD_MOCK=1 python3 test_scenarios.py` is not a mock test; the script forces `TINYWORLD_MOCK=0` internally and failed in this sandbox because DNS to Modal is blocked (`Temporary failure in name resolution`). Re-run it from a network-enabled shell.

## Done & verified — V9 (bug pass, by Codex, 2026-06-14)
- Fixed app startup port bug: `app.py` now respects `GRADIO_SERVER_PORT` instead of hard-coding `7860`.
- Fixed mic-warning copy in `assets/game.js`: it now points to the current browser port (`localhost:<port>`) instead of always `localhost:7860`.
- Fixed unsafe HTML rendering in `app.py`: reaction text, follow-up text, gossip snippets, teaching focus text, parsed model reasoning/actions, and transcription status are escaped before insertion into `gr.HTML`.
- Fixed deploy metadata drift: README and requirements now pin Gradio `6.18.0+`, README model tags/table now reflect `nvidia/Nemotron-Mini-4B-Instruct`, Modal Whisper transcription, and Cohere fallback.
- Fixed Modal async warning: FastAPI endpoints now use `await ...remote.aio(...)` instead of blocking `.remote(...)` calls inside async endpoints.
- Redeployed Modal successfully after the async endpoint fix.
- Verified: `py_compile`, `validate_worlds.py`, `node --check assets/game.js`, malicious-text render escaping, and valid Gradio callback flow on `http://localhost:8062` (`do_trigger`, `random_chaos`, `run_scenario`, `switch_world`, `transcribe_audio`).

## In progress
- None — V9 bug pass complete and tested.

## Deploy note ("post it")
- Local run is fully working: `TINYWORLD_MOCK=1 python3 app.py` → http://localhost:7860, or set `GRADIO_SERVER_PORT=<port>` if 7860 is busy.
- Going live on HF Spaces needs the user's HF account + `COHERE_API_KEY`/Modal token as Space secrets,
  and the real (non-mock) model path. Commits/push remain **Codex-only** per project rule.

## Next up
- Live endpoint probe from this machine once sandbox approval/network permits: call `voice.generate_voice(...)`, then feed that WAV into `transcribe.transcribe(...)`.
- Distinct realistic redesign pass for `starhaven` and `old_town`.
- Sponsor credits + submission cleanup.

## Blockers / decisions
- Nemotron-Mini-4B is currently wired as the primary public NVIDIA model; MiniCPM5-1B remains loaded on Modal as fallback.
- Gradio 6.x: css/js passed to launch() not Blocks constructor.
- Modal Whisper transcription is deployed; `COHERE_API_KEY` is now only needed for Cohere fallback/sponsor path.
- External live endpoint calls from this sandbox currently need escalation; the approval review timed out twice for the voice probe. A non-escalated probe fails DNS as expected under the sandbox.
- Diorama PNG not yet created — stage uses CSS gradient fallback.

## How to resume
- Read `AGENTS.md`, then `REDESIGN_V2.md`, then this file. Run `TINYWORLD_MOCK=1 python3 app.py` to test locally on http://localhost:7860. For real pipeline validation, run `./start.sh`, trigger one typed event, then record mic audio and press Transcribe; first real voice/transcribe requests may cold-start Modal.
