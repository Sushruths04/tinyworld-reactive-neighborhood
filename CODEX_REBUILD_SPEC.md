# TinyWorld — Rebuild Spec for Codex (v10)

> **Audience:** Codex (code generation). **Author:** planning pass, no code written.
> **Rule unchanged:** all code + commits are produced by Codex. Do not let other tools commit.
> **Read order:** this file → `AGENTS.md` (original build spec) → `CHECKPOINT.md` (history).
>
> This document supersedes the behavioural parts of `AGENTS.md` where they conflict.
> The goal of v10 is to turn TinyWorld from a "random reaction box" into a **small
> agent-based life-sim** where each character is a believable person with a daily
> routine, real LLM-driven decisions, and obeys directed commands — all behind hard
> guardrails, with automated tests and a user acceptance script.

---

## 0. Why we are rebuilding (root causes — fix these, do not paper over them)

These are the concrete defects in the current code. Every one must be eliminated.

| # | Defect | Evidence (current code) | Required outcome |
|---|--------|-------------------------|------------------|
| R1 | Silent mock fallback hides LLM failure | `agents.py` `_real_react` `except` → `_mock_react`; no UI badge | Real/mock state is **explicit and visible**; a failed real call surfaces an error, never disguises canned text as the model. |
| R2 | LLM writes one sentence; movement/action/mood are random heuristics | `_mock_brain`, `random.choice(MOODS)`, `_compute_drama` | The model returns a **structured decision** (say + action + destination + mood) that the engine validates and uses. |
| R3 | Directed commands ignored; event broadcast to all | `react()` loops all cast; no addressee parsing | Player input is **classified** (world-event vs directed-command) and **routed** to the right character(s). |
| R4 | Movement randomized twice, overrides the agent's choice | `_mock_brain` home-override + `build_reactions_payload` gather/scatter | A character's chosen destination is **authoritative**; the renderer never reassigns it randomly. |
| R5 | No persistence / no sense of time | mood re-rolled per event; no clock | A **simulation clock + daily schedule + needs** drive behaviour between events. |
| R6 | Three worlds share one board | starhaven/old_town reuse geometry | **Two genuinely distinct worlds** with different boards, roles, and schedules. |
| R7 | No automated tests of behaviour | `test_scenarios.py` only checks for canned strings, needs live net | Deterministic **unit + integration tests** with a fake LLM; live smoke test gated by flag. |

---

## 1. Target architecture (the mental model)

TinyWorld is a **tick-driven town simulation** with an **event/command layer** on top.

```
                 ┌────────────────────────────────────────────────┐
   player input  │  INPUT ROUTER  (classify: world-event |          │
  ───────────────▶  directed-command | ambient)                     │
                 └───────────────┬────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │  SIM ENGINE (authoritative state)                          │
        │   • clock: game time, day, time-of-day                     │
        │   • per-character: position, schedule, current goal,       │
        │     needs(energy/hunger/social), mood, memory, log         │
        │   • each TICK: advance routine OR react to active event    │
        └───────────────┬───────────────────────────┬──────────────┘
                         ▼                           ▼
            ┌────────────────────────┐   ┌──────────────────────────┐
            │ DECISION (LLM)          │   │ GUARDRAILS                │
            │ one structured call per │──▶│ schema-validate, clamp,   │
            │ character → JSON        │   │ whitelist goto, de-meta,  │
            │ {think,say,act,goto,    │   │ retry, circuit-breaker    │
            │  mood,need_deltas}      │   └──────────────────────────┘
            └────────────────────────┘
                         ▼
            ┌────────────────────────┐
            │ RENDER  (canvas + HUD) │  walks pawns to validated goto,
            │ honours engine state   │  shows logs/timeline, voice
            └────────────────────────┘
```

Key principle: **the LLM proposes, the engine disposes.** The model returns a decision; the
engine validates it against hard rules and is the single source of truth for positions, time,
and state. The renderer only displays engine state — it must never invent movement.

---

## 2. Data contracts (define these first; everything else depends on them)

### 2.1 Character (world file) — add routine + role

Extend each cast member with a **role** and a **schedule**. Schedule entries are
`(start_hour, end_hour, hotspot_key, activity_label, need_effects)`.

```python
{
  "name": "Luca Bell",
  "role": "student",                       # drives default schedule + voice
  "age": 15, "job": "...", "traits": [...], "backstory": "...",
  "relationships": {...}, "voice_description": "(...)",
  "model": "nvidia/Nemotron-Mini-4B-Instruct",
  "emoji": "🧒", "home": "home_luca",
  "catchphrase_hint": "...",
  "schedule": [                            # 24h, in game hours; gaps default to "home"
    [7,  8,  "home_luca", "getting ready",        {"energy": -2}],
    [8,  15, "school",    "in class",             {"energy": -8, "social": +6}],
    [15, 17, "cafe",      "hanging out after school", {"hunger": -10, "social": +8}],
    [17, 22, "home_luca", "homework + notebook",  {"energy": -4}],
    [22, 7,  "home_luca", "sleeping",             {"energy": +30}]
  ],
  "needs": {"energy": 70, "hunger": 30, "social": 50}   # 0..100 starting values
}
```

Roles to support at minimum: `student`, `worker`, `shopkeeper`, `medic`, `retiree`.
Provide a `DEFAULT_SCHEDULES[role]` table so a world can omit `schedule` and inherit one.

### 2.2 LLM decision (the structured reply) — STRICT JSON

The model is asked to return **only** this JSON (no prose around it):

```json
{
  "think": "one short private thought (<=120 chars)",
  "say":   "what they say out loud, 1-2 sentences, in-character",
  "action":"a concrete verb phrase, e.g. 'rush to the clinic to help'",
  "goto":  "<hotspot_key from the allowed list, or 'stay'>",
  "mood":  "<one of the allowed mood words>",
  "need_deltas": {"energy": -5, "hunger": 0, "social": +3}
}
```

The prompt MUST include: the character persona + current `mood`, current **time of day**
and what they were **currently doing** (from schedule), their recent **memory**, the
**allowed hotspot keys** (exact list), and the triggering input. For a **directed command**,
the prompt must name the addressee and the instruction explicitly and instruct the model to
comply unless strongly out of character (and if it refuses, say why in `say`).

### 2.3 Engine → renderer payload

`build_reactions_payload` is **rewritten** to be a pure pass-through of engine decisions:
each reaction carries the **validated** `goto` tile (already resolved by the engine), the
`say`, `mood`, `activity`. **Remove** the `gather/scatter/mixed` randomization and the
`pool[i % len]` fallback entirely (defect R4).

---

## 3. Work plan (phased; each phase ends green + committed by Codex)

### Phase 1 — Honesty & health (kill the silent mock) — *do this first*
1. Add `health_check.py`: pings `MODAL_REACT_URL` (and voice/transcribe) with a tiny
   warm-up payload; prints `LLM: LIVE (model id, latency)` or `LLM: UNREACHABLE (reason)`.
   `start.sh` runs it before launching and prints the verdict.
2. Add a **mode badge** to the top bar (`app.py`): 🟢 `Live · Nemotron-Mini-4B` /
   🟡 `Offline demo (mock)` / 🔴 `LLM error`. Wire it to the real runtime state, not env only.
3. In `agents.py`, split failure handling: in **real mode**, a Modal failure returns a
   reaction with `error=True` and a visible "[model unreachable — retrying]" status; it must
   **not** be silently replaced by canned `MOCK_REACTIONS`. Mock mode stays explicit (badge yellow).
4. Cold-start UX: first real call shows a "waking the model (~90s)" state; bump client timeout
   to ≥180s for the first call, add one retry, then a warm path.

**Done when:** with Modal up you see 🟢 and real text; with Modal down you see 🔴 + an error,
never a canned line masquerading as the model.

### Phase 2 — Decision engine (LLM proposes, engine disposes) — fixes R2/R4
1. New module `decide.py`: builds the structured prompt (§2.2), calls Modal, parses JSON,
   returns a validated `Decision`. All guardrails (§4) live here.
2. Rewrite `agents.react()` to: for each character, build context from **engine state**
   (current schedule activity, time, needs, mood, memory), call `decide`, get a `Decision`.
   Mood comes from the Decision (clamped to allowed set), **not** `random.choice`.
3. Resolve `goto`: validate against the world's real `hotspots_tile` keys; `"stay"` keeps
   position; invalid → `"stay"` + log a guardrail warning. The resolved tile is authoritative.
4. Delete `_mock_brain` movement override and the payload randomizer (R4). Mock mode still
   works but its mock `Decision` must also obey the same schema (so tests can use it).

### Phase 3 — Input router: commands vs events — fixes R3
1. New `router.py` `classify(text, cast)` → one of:
   - `directed_command` → `{addressee: <name>, instruction: <text>}` when input starts with /
     contains a cast first-name + an imperative ("Marta, go to the clinic", "tell Jay to…").
   - `world_event` → everyone reacts (e.g. "the power goes out").
   - `ambient` → low-stakes flavour, optional.
2. Matching: case-insensitive first-name match against the active cast; support "tell X to…",
   "X, …", "make X …". If two names match, treat as multi-addressee.
3. `do_trigger` routes: a directed command reacts **only** the addressee(s) (others may get a
   short "notices" beat), and the addressee's `goto`/action must reflect the instruction.
   Destination words in the command ("clinic", "café", "school") must map to the right hotspot
   via a `LOCATION_ALIASES` table per world and be honoured.

**Done when:** "Marta, go to the clinic" → **only Marta** walks to the clinic building, her
log shows it, others stay on routine. (This is acceptance test A1 in §6.)

### Phase 4 — Living town: clock, schedules, needs, timeline — fixes R5
1. `world_state.py` gains: `game_time` (hours, float), `day`, and a `tick()` that advances
   time and, for every character **not** currently handling an event, moves them along their
   schedule (set position to scheduled hotspot, apply `need_effects`, append a timeline entry).
2. Needs (`energy/hunger/social`, 0..100) drift each tick and are surfaced in the roster
   meters (replace the abstract energy/social vibe bars with real needs). Low needs nudge mood
   and can override routine (e.g. hunger>80 → detour to café) — but only via the same
   Decision/guardrail path, never raw random.
3. **Per-character timeline log**: a visible "Daily Log" panel showing each person's day:
   `07:30 left home · 08:00 at school (in class) · 12:00 lunch at café …`. This is the
   "particular log of their time" the user asked for.
4. Auto-tick: the canvas already polls; add a slow sim tick (e.g. 1 game-hour per N seconds,
   pausable) so the town visibly lives between events. A "⏯ time" control lets the user
   pause/step. Throwing an event interrupts routines; after resolution characters resume.

**Done when:** with no input, characters move through their day on schedule, needs change,
and each has a readable timeline. Emergencies interrupt then resume the routine.

### Phase 5 — World redesign (distinct themes) — fixes R6
1. **Keep** `maple_street` (residential) — it is the best one. Refine its schedules so roles
   are visibly different (Luca→school, Jay→deliveries+café, Nia→clinic shifts, Priya→office,
   Marta→retired/park).
2. **Replace** the two lookalikes with **ONE new, genuinely distinct world** — proposal:
   **"Riverside Campus"** (a small school-town) with its **own board geometry** (different
   cols/rows, a central quad instead of a square, riverside road) and a cast whose roles make
   schedules obviously different: a teacher, two students, a café owner, a school nurse,
   a groundskeeper. Different building kinds + palette + props from Maple.
   - Delete `starhaven.py` and `old_town.py` (or keep ONE rebuilt with truly different
     geometry if the user prefers two — see open question Q1).
3. `validate_worlds.py` is extended (§5) to **fail** if two worlds share identical board
   dimensions + building layout, so lookalikes can't regress.

### Phase 6 — Tests, guardrails hardening, acceptance — fixes R7
See §4, §5, §6. Land the deterministic test suite, the world validator, and the user
acceptance script. CI-style: `make test` (or `python -m pytest`) must pass offline.

---

## 4. Guardrails (mandatory — "guardrail everything")

All of these live in `decide.py` / `world_state.py` and must have unit tests.

**LLM output guardrails**
- **Schema validation:** parse JSON; on malformed output, **retry once** with a stricter
  "return ONLY JSON" reminder; on second failure, fall back to a deterministic safe Decision
  (`goto:"stay"`, persona line) and mark `degraded=True` (shown subtly, not hidden).
- **`goto` whitelist:** only keys in the active world's `hotspots_tile`; anything else → `stay`.
- **Mood whitelist:** clamp to the allowed `MOODS` set; unknown → keep previous mood.
- **Numeric clamp:** every `need_delta` clamped to `[-25, +25]`; resulting needs clamped `[0,100]`.
- **Dialogue hygiene:** keep `_clean_line` as a *guardrail* (strip meta/stage-dir/brackets),
  cap length (≤220 chars), strip control chars; if empty after cleaning → persona fallback.
- **No injection echo:** never interpolate raw player text into HTML without `html.escape`
  (already partly done — audit every `gr.HTML`).

**Service guardrails**
- **Timeout + retry:** per-call timeout (first call ≥180s for cold start, warm ≤30s), one retry.
- **Circuit breaker:** after N consecutive Modal failures, flip badge to 🔴 and stop hammering
  for a cooldown; surface clearly. Never silently degrade to mock in real mode.
- **Determinism switch:** `TINYWORLD_SEED` env seeds all `random` use so tests are reproducible.

**Input guardrails**
- Empty / whitespace input → no-op with a hint.
- Oversized input (>500 chars) → truncate + warn.
- Command classifier must be safe on punctuation-only / emoji-only input (→ ambient/no-op).

---

## 5. Test requirements (must be automated + offline)

Use `pytest`. Add a **FakeLLM** that returns canned, well-formed `Decision` JSON keyed by
prompt content, so behaviour is deterministic with **no network**.

**Unit tests** (`tests/`):
- `test_router.py`: "Marta, go to the clinic" → directed_command(addressee=Marta,
  location=clinic); "the power goes out" → world_event; "🙂" → ambient/no-op; two-name input
  → multi-addressee.
- `test_decide.py`: malformed JSON → retry → safe fallback (`degraded`); out-of-range
  need_delta clamped; bad `goto` → `stay`; bad mood → previous mood; meta-leak line cleaned.
- `test_schedule.py`: at 08:30 a student is at `school`; needs drift correctly; hunger>80
  triggers a café detour through the Decision path (with FakeLLM).
- `test_world_state.py`: tick advances time/day; timeline entries appended; positions update.
- `test_worlds.py` (replaces ad-hoc `validate_worlds.py` checks): every character `home`,
  every schedule hotspot, and every `LOCATION_ALIASES` target exists in `hotspots_tile`;
  no two worlds share identical board dims + building layout; every cast has a valid role.

**Integration tests** (FakeLLM, no network):
- `test_directed_command.py`: throw "Marta, go to the clinic" → engine moves **only** Marta
  to the clinic tile; her timeline logs it; others unchanged. (Mirrors acceptance A1.)
- `test_world_event.py`: throw a world event → all react; each Decision validated; town state
  updates; no random target reassignment (assert each pawn target == its Decision goto tile).

**Live smoke test** (gated by `RUN_LIVE=1`, real Modal): one warm-up + one real reaction;
asserts non-empty, non-canned text and JSON schema. Documented as manual / network-shell only
(the dev sandbox blocks Modal DNS — see Blockers).

**Definition of "tests pass":** `python -m pytest -q` is green **offline** (FakeLLM); the live
smoke test passes from a network-enabled shell.

---

## 6. User acceptance script (hand to the user to verify the app "works")

Run `./start.sh`, open **http://localhost:7860** (not 0.0.0.0). Expect the badge top-right to
read 🟢 `Live · Nemotron-Mini-4B` within ~90s of the first action (cold start).

| # | Do this | Expect |
|---|---------|--------|
| A1 | Type `Marta, go to the clinic` → THROW | **Only Marta** walks to the CLINIC building; her Daily Log gains a "→ clinic" entry; others keep their routine. |
| A2 | Type `the power goes out across the block` → THROW | All 5 react in **distinct voices**; movements differ and make sense (medic checks people, planner heads to office); badge stays 🟢. |
| A3 | Press ⏯ time and watch ~1 minute with no input | Characters move through their **schedule** (student → school, worker → office, then café); needs meters change; timelines fill. |
| A4 | Type `tell Jay to go home and rest` → THROW | **Only Jay** heads to his home; his line acknowledges the instruction. |
| A5 | Record mic → Transcribe → THROW | Spoken event transcribes to text (real Whisper on Modal) then reacts. |
| A6 | Switch World → Riverside Campus | A **visibly different town** (different layout/buildings) with a different cast whose schedules differ from Maple. |
| A7 | Kill network / stop Modal, THROW | Badge flips 🔴 with a clear "model unreachable" message — **no fake canned reply pretending to be the model**. |

If any row fails, that is a bug to file against the phase that owns it.

---

## 7. Blockers to clear (carry-over + new)

- **B1 Sandbox can't reach Modal (DNS).** The dev sandbox blocks Modal DNS, so live tests must
  run from a **network-enabled shell**. Add `health_check.py` + document `RUN_LIVE=1`.
- **B2 Gated NVIDIA Nano models.** Nano-3/Nano-4B are HF-gated (401) with no token. Stay on
  **public `nvidia/Nemotron-Mini-4B-Instruct`**, OR set `HF_TOKEN` as a Modal secret and switch.
  Document the choice; the badge must show the model actually loaded (read it back from Modal).
- **B3 First-call cold start ~90s.** Add warm-up ping on launch + "waking model" UX (Phase 1).
- **B4 Commits are Codex-only.** Keep. Codex makes all commits to the public repo for the prize.
- **B5 Voice not load-tested live.** Add a live voice smoke test (gated) and verify warm latency.
- **B6 Deploy to HF Spaces** still needs the user's HF account + Modal token/Cohere key as Space
  secrets. Out of scope for code; document the exact secrets needed in README.

---

## 8. Decisions (LOCKED by the user — Codex: build to these, do not re-ask)

- **Q1 — Worlds: Maple + ONE new.** Keep `maple_street`. **Delete** `starhaven.py` and
  `old_town.py` (and their registry entries). Build exactly one new distinct world.
- **Q2 — Second world: "Riverside Campus" (school-town).** Cast roles: a **teacher**, **two
  students**, a **café owner**, a **school nurse**, and a **groundskeeper**. Its board must use
  **different dimensions + layout** from Maple (a central quad + a riverside road, not a square),
  its own palette and building kinds. Schedules must be visibly different from Maple's
  residential mix (students in class 8–15, teacher teaching, nurse on clinic hours, etc.).
- **Q3 — Time scale: 1 game-hour per ~6 real seconds**, pausable/steppable (a full day ≈ 2.5
  min). Expose `TINYWORLD_TIME_SCALE` so it's tunable; the ⏯ control pauses/steps.

---

## 9. Definition of done (v10)

1. 🟢/🟡/🔴 badge reflects real Modal state; **no silent mock** in real mode (R1).
2. Each reaction is an LLM **Decision** (say+action+goto+mood) the engine validates; movement
   is authoritative, never re-randomized (R2, R4).
3. Directed commands work: addressee parsed, obeyed, others stay on routine (R3).
4. Town **lives**: clock + per-role schedules + needs + per-character timeline; emergencies
   interrupt then resume (R5).
5. **Two visibly distinct worlds**; validator blocks lookalikes (R6).
6. `pytest` green **offline** via FakeLLM; live smoke test passes from a network shell (R7).
7. All guardrails (§4) implemented and unit-tested.
8. User acceptance script (§6) passes end-to-end on localhost.
9. README updated (model actually loaded, secrets, how to run + test). Codex commits all of it.
</content>
</invoke>
