import random
import threading
from collections import defaultdict, deque

_lock = threading.Lock()

_states = {}

DEFAULT_SCHEDULES = {
    "student": [
        [7, 8, "school", "getting ready for class", {"energy": -2, "social": 1}],
        [8, 15, "school", "in class", {"energy": -8, "social": 6}],
        [15, 17, "cafe", "after-school break", {"hunger": -10, "social": 8}],
        [17, 22, "school", "homework and hobbies", {"energy": -4}],
        [22, 7, "school", "sleeping", {"energy": 25}],
    ],
    "worker": [
        [7, 9, "cafe", "breakfast before work", {"hunger": -8, "energy": 3}],
        [9, 17, "priya_office", "working", {"energy": -10, "social": 3}],
        [17, 19, "park", "walking after work", {"energy": -2, "social": 4}],
        [19, 23, "cafe", "evening errands", {"hunger": -8, "social": 3}],
        [23, 7, "priya_office", "resting", {"energy": 24}],
    ],
    "shopkeeper": [
        [6, 8, "shop", "opening up", {"energy": -2}],
        [8, 18, "shop", "serving customers", {"energy": -9, "social": 8}],
        [18, 21, "cafe", "closing-day dinner", {"hunger": -10, "social": 3}],
        [21, 6, "shop", "resting", {"energy": 22}],
    ],
    "medic": [
        [7, 8, "cafe", "coffee before shift", {"hunger": -6, "energy": 2}],
        [8, 18, "nia_clinic", "clinic shift", {"energy": -12, "social": 5}],
        [18, 20, "park", "decompressing", {"energy": -2, "social": 2}],
        [20, 7, "nia_clinic", "resting on call", {"energy": 24}],
    ],
    "retiree": [
        [6, 9, "marta_home", "quiet morning routine", {"energy": 4}],
        [9, 12, "shop", "checking the old storefront", {"energy": -3, "social": 3}],
        [12, 16, "park", "watching the neighborhood", {"energy": -2, "social": 4}],
        [16, 20, "cafe", "tea and gossip", {"hunger": -8, "social": 5}],
        [20, 6, "marta_home", "resting at home", {"energy": 20}],
    ],
}


def _new_state(world_id):
    return {
        "world_id": world_id,
        "day": 1,
        "event_count": 0,
        "chaos": 0.0,
        "town_mood": 0.0,
        "game_time": 7.0,
        "paused": False,
        "vibes": {},
        "needs": {},
        "affinity": {},
        "moods": {},
        "memory": defaultdict(lambda: deque(maxlen=4)),
        "timeline": defaultdict(lambda: deque(maxlen=20)),
        "reflections": {},
        "positions": {},
        "activities": {},
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
            if name not in state["needs"]:
                state["needs"][name] = c.get("needs", {"energy": 60, "hunger": 35, "social": 50}).copy()
            if name not in state["moods"]:
                state["moods"][name] = random.choice([
                    "happy", "stressed", "bored", "excited", "hungry",
                    "tired", "nostalgic", "curious", "proud", "embarrassed",
                ])
            if name not in state["reflections"]:
                state["reflections"][name] = ""
            if name not in state["positions"]:
                state["positions"][name] = c.get("home", "square")
            if name not in state["activities"]:
                state["activities"][name] = "starting the day"
            if not state["timeline"][name]:
                state["timeline"][name].append(f"{format_time(state['game_time'])} at {state['positions'][name].replace('_', ' ')}")
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


def get_needs(world_id):
    state = get_state(world_id)
    with _lock:
        return {name: vals.copy() for name, vals in state["needs"].items()}


def get_activity(world_id, name):
    state = get_state(world_id)
    with _lock:
        return state["activities"].get(name, "")


def get_timeline(world_id):
    state = get_state(world_id)
    with _lock:
        return {name: list(entries) for name, entries in state["timeline"].items()}


def get_game_time(world_id):
    state = get_state(world_id)
    with _lock:
        return state["day"], state["game_time"], state["paused"]


def set_paused(world_id, paused):
    state = get_state(world_id)
    with _lock:
        state["paused"] = bool(paused)
        return state["paused"]


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


def tick(world, hours=1.0, force=False):
    state = get_state(world["id"])
    with _lock:
        if state["paused"] and not force:
            return False
        previous_hour = state["game_time"]
        state["game_time"] += hours
        while state["game_time"] >= 24:
            state["game_time"] -= 24
            state["day"] += 1
        for c in world["cast"]:
            name = c["name"]
            entry = schedule_entry(c, state["game_time"])
            if not entry:
                continue
            _, _, hotspot, activity, effects = entry
            if hotspot not in (world.get("board", {}) or {}).get("hotspots_tile", {}):
                hotspot = c.get("home", "square")
            old_pos = state["positions"].get(name)
            old_activity = state["activities"].get(name)
            state["positions"][name] = hotspot
            state["activities"][name] = activity
            needs = state["needs"].setdefault(name, {"energy": 60, "hunger": 35, "social": 50})
            needs["hunger"] = _clamp_need(needs.get("hunger", 35) + 4 + effects.get("hunger", 0))
            needs["energy"] = _clamp_need(needs.get("energy", 60) + effects.get("energy", 0))
            needs["social"] = _clamp_need(needs.get("social", 50) + effects.get("social", 0))
            if old_pos != hotspot or old_activity != activity or int(previous_hour) != int(state["game_time"]):
                state["timeline"][name].append(
                    f"{format_time(state['game_time'])} -> {hotspot.replace('_', ' ')} ({activity})"
                )
        return True


def schedule_entry(character, hour):
    schedule = character.get("schedule") or DEFAULT_SCHEDULES.get(character_role(character), [])
    for entry in schedule:
        start, end = entry[0], entry[1]
        if start <= end:
            active = start <= hour < end
        else:
            active = hour >= start or hour < end
        if active:
            return entry
    home = character.get("home", "square")
    return [0, 24, home, "at home", {"energy": 0, "hunger": 0, "social": 0}]


def character_role(character):
    role = character.get("role")
    if role:
        return role
    job = character.get("job", "").lower()
    if "student" in job:
        return "student"
    if "paramedic" in job or "nurse" in job or "medic" in job:
        return "medic"
    if "retired" in job:
        return "retiree"
    if "cafe" in job or "shop" in job or "owner" in job:
        return "shopkeeper"
    return "worker"


def format_time(hour):
    hour = hour % 24
    h = int(hour)
    m = int(round((hour - h) * 60)) % 60
    return f"{h:02d}:{m:02d}"


def _clamp_need(value):
    return max(0, min(100, int(value)))


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
