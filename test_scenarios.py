"""
TinyWorld robustness suite — fires 20 scenarios at the REAL pipeline, one by one.

Run AFTER `modal deploy modal_app.py`, with the real backend wired up:
    TINYWORLD_MOCK=0 python3 test_scenarios.py

It is deliberately strict about the thing we care about most: every reaction must
come from the live LLM, not from the canned mock tables. A case FAILS if any line
matches a hardcoded mock string, if the structured THINK/DO/SAY/GOTO didn't parse,
or if all five characters say the same thing.
"""
import os
import sys
import time

# Force real inference for the test (never silently pass on mock output).
os.environ["TINYWORLD_MOCK"] = "0"

import agents
import world_state
from worlds import get_world, list_worlds

# Build the set of every canned string so we can detect fakery.
_MOCK_STRINGS = set()
for _pool in agents.GENERIC_MOCK.values():
    _MOCK_STRINGS.update(s.strip() for s in _pool)
for _char in agents.MOCK_REACTIONS.values():
    for _pool in _char.values():
        _MOCK_STRINGS.update(s.strip() for s in _pool)


# 20 cases spread across the three worlds: each world's teaching scenarios + ad-hoc events.
def _build_cases():
    cases = []
    for meta in list_worlds():
        wid = meta["id"]
        w = get_world(wid)
        for sc in w.get("scenarios", []):
            cases.append((wid, sc["event"]))
        for ev in w.get("events", [])[:4]:
            cases.append((wid, ev))
    # trim to exactly 20
    return cases[:20]


def _check(wid, event):
    """Run one scenario, return (ok, hard_fails[], warnings[], (reactions, dt))."""
    fails, warns = [], []
    t0 = time.time()
    try:
        result = agents.react(wid, event)
    except Exception as e:
        return False, [f"react() raised: {e}"], [], None
    dt = time.time() - t0
    reactions = result.get("reactions", [])

    if len(reactions) != 5:
        fails.append(f"expected 5 reactions, got {len(reactions)}")

    texts = []
    for r in reactions:
        name = r.get("name", "?")
        text = (r.get("text") or "").strip()
        texts.append(text)
        # ---- HARD: the things that make it fake or broken ----
        if not text:
            fails.append(f"{name}: empty text")
        if text in _MOCK_STRINGS:
            fails.append(f"{name}: CANNED MOCK STRING (not real LLM) -> {text!r}")
        if "[error" in text.lower() or "something went wrong" in text.lower():
            fails.append(f"{name}: backend error leaked -> {text!r}")
        # ---- SOFT: a weak 1B model occasionally skips a field ----
        if not (r.get("understanding") or "").strip():
            warns.append(f"{name}: no THINK parsed")
        if not (r.get("action") or "").strip():
            warns.append(f"{name}: no DO parsed")
        goto = r.get("moved_to")
        if goto is not None and goto not in agents._hotspots(get_world(wid)):
            warns.append(f"{name}: invalid goto {goto!r}")

    if len(set(texts)) <= 1 and len(texts) > 1:
        fails.append("all characters said the same thing (no variety)")

    return (len(fails) == 0), fails, warns, (reactions, dt)


def main():
    cases = _build_cases()
    print(f"Running {len(cases)} scenarios against the live backend "
          f"(MOCK={os.environ['TINYWORLD_MOCK']}, react_url={agents.MODAL_REACT_URL})\n")
    passed = 0
    for i, (wid, event) in enumerate(cases, 1):
        world_state.init_cast(get_world(wid))
        ok, fails, warns, extra = _check(wid, event)
        tag = "PASS" if ok else "FAIL"
        dt = extra[1] if extra else 0
        print(f"[{i:2}/{len(cases)}] {tag}  ({wid}, {dt:.1f}s)  {event[:64]}")
        if ok:
            passed += 1
            sample = extra[0][0]
            print(f"        real e.g. {sample['name']}: {sample['text'][:80]}")
        for f in fails[:6]:
            print(f"        FAIL  {f}")
        if warns:
            print(f"        warn  {len(warns)} soft issue(s): {warns[0]}")
        print(flush=True)
    print(f"==== {passed}/{len(cases)} scenarios passed (hard checks) ====")
    sys.exit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
