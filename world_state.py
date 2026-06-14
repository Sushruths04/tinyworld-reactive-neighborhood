import random
import threading
from collections import defaultdict, deque

_lock = threading.Lock()

_states = {}


def _new_state(world_id):
    return {
        "world_id": world_id,
        "day": 1,
        "event_count": 0,
        "chaos": 0.0,
        "town_mood": 0.0,
        "vibes": {},
        "affinity": {},
        "moods": {},
        "memory": defaultdict(lambda: deque(maxlen=4)),
        "reflections": {},
        "positions": {},
    }


def get_state(world_id):
    with _lock:
        if world_id not in _states:
            _states[world_id] = _new_state(world_id)
        return _states[world_id]


def reset_world(world_id):
    with _lock:
        _states[world_id] = _new_state(world_id)
        return _states[world_id]


def init_cast(world):
    state = get_state(world["id"])
    with _lock:
        for c in world["cast"]:
            name = c["name"]
            if name not in state["vibes"]:
                state["vibes"][name] = {"energy": 0.6, "social": 0.5}
            if name not in state["moods"]:
                state["moods"][name] = random.choice([
                    "happy", "stressed", "bored", "excited", "hungry",
                    "tired", "nostalgic", "curious", "proud", "embarrassed",
                ])
            if name not in state["reflections"]:
                state["reflections"][name] = ""
            if name not in state["positions"]:
                state["positions"][name] = c.get("home", "square")
        pairs = [(a["name"], b["name"]) for a in world["cast"] for b in world["cast"] if a["name"] < b["name"]]
        for a, b in pairs:
            if (a, b) not in state["affinity"]:
                state["affinity"][(a, b)] = 0.0


def get_mood(world_id, name):
    state = get_state(world_id)
    with _lock:
        return state["moods"].get(name, "curious")


def set_mood(world_id, name, mood):
    state = get_state(world_id)
    with _lock:
        state["moods"][name] = mood


def get_memory(world_id, name):
    state = get_state(world_id)
    with _lock:
        return list(state["memory"][name])


def add_memory(world_id, name, event, reaction_text):
    state = get_state(world_id)
    entry = f"Event: {event} | Reaction: {reaction_text}"
    with _lock:
        state["memory"][name].append(entry)


def add_gossip(world_id, target_name, snippet):
    state = get_state(world_id)
    entry = f"Gossip: {snippet}"
    with _lock:
        state["memory"][target_name].append(entry)


def get_reflection(world_id, name):
    state = get_state(world_id)
    with _lock:
        return state["reflections"].get(name, "")


def set_reflection(world_id, name, text):
    state = get_state(world_id)
    with _lock:
        state["reflections"][name] = text


def get_vibes(world_id):
    state = get_state(world_id)
    with _lock:
        return dict(state["vibes"])


def get_affinity(world_id):
    state = get_state(world_id)
    with _lock:
        return dict(state["affinity"])


def get_position(world_id, name):
    state = get_state(world_id)
    with _lock:
        return state["positions"].get(name)


def set_position(world_id, name, hotspot):
    state = get_state(world_id)
    with _lock:
        state["positions"][name] = hotspot


def apply_vibe_delta(world_id, name, delta):
    state = get_state(world_id)
    with _lock:
        v = state["vibes"].setdefault(name, {"energy": 0.5, "social": 0.5})
        v["energy"] = max(0.0, min(1.0, v["energy"] + delta.get("energy", 0)))
        v["social"] = max(0.0, min(1.0, v["social"] + delta.get("social", 0)))


def apply_affinity_delta(world_id, name, delta):
    state = get_state(world_id)
    with _lock:
        for other, d in delta.items():
            pair = tuple(sorted([name, other]))
            state["affinity"][pair] = max(-1.0, min(1.0, state["affinity"].get(pair, 0.0) + d))


def increment_event(world_id, chaos_delta=0.1):
    state = get_state(world_id)
    with _lock:
        state["event_count"] += 1
        state["chaos"] = min(1.0, state["chaos"] + chaos_delta)
        if state["event_count"] % 5 == 0:
            state["day"] += 1


def get_town_mood(world_id):
    state = get_state(world_id)
    with _lock:
        return state["town_mood"]


def set_town_mood(world_id, val):
    state = get_state(world_id)
    with _lock:
        state["town_mood"] = max(-1.0, min(1.0, val))


def get_event_count(world_id):
    state = get_state(world_id)
    with _lock:
        return state["event_count"]


def get_day(world_id):
    state = get_state(world_id)
    with _lock:
        return state["day"]


def get_chaos(world_id):
    state = get_state(world_id)
    with _lock:
        return state["chaos"]


def maybe_form_reflection(world_id, name):
    state = get_state(world_id)
    with _lock:
        memories = list(state["memory"][name])
        if not memories:
            return
        last = memories[-1]
        learned = last.split("| Reaction:")[-1].strip() if "| Reaction:" in last else last
        learned = learned.rstrip(".")
        templates = [
            f"I'm learning how this block reacts. Last time, my move was to {learned.lower()}.",
            f"Each thing that happens teaches me something. I keep choosing to act, not just watch.",
            f"I remember what I did last time, and I'd do it again: {learned}.",
            f"These events are changing how I read my neighbors — and myself.",
            f"I trust my instincts more now. {learned} felt right.",
        ]
        state["reflections"][name] = random.choice(templates)
