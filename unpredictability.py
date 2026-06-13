import random
import threading
from collections import defaultdict, deque

MOODS = [
    "happy",
    "stressed",
    "bored",
    "excited",
    "hungry",
    "tired",
    "nostalgic",
    "curious",
    "proud",
    "embarrassed",
]

SURPRISE_SEEDS = [
    "Slip in one oddly specific detail from earlier today.",
    "React as if this event confirms a private theory you never told anyone.",
    "Let a petty personal concern steer part of your response.",
    "Compare the event to a memory that still annoys you.",
    "Say one thing confidently, then soften or complicate it.",
    "Ask one pointed question that reveals your bias.",
    "Treat one small part of the event as the real emergency.",
    "Reveal a secret wish connected to the situation.",
    "Interpret the event through your relationship with someone nearby.",
    "End with a surprising offer, warning, or demand.",
]

_lock = threading.Lock()
_character_moods = {}
_character_memories = defaultdict(lambda: deque(maxlen=3))
_character_reflections = defaultdict(lambda: {"text": "", "event_count": 0})


def get_mood(name):
    with _lock:
        if name not in _character_moods:
            _character_moods[name] = random.choice(MOODS)
        return _character_moods[name]


def reroll_mood(name):
    with _lock:
        _character_moods[name] = random.choice(MOODS)
        return _character_moods[name]


def get_recent_memories(name):
    with _lock:
        return list(_character_memories[name])


def update_memory(name, event, reaction_text):
    memory_entry = f"Event: {event} | Reaction: {reaction_text}"
    with _lock:
        _character_memories[name].append(memory_entry)
        return list(_character_memories[name])


def format_relationships(character):
    relationships = character.get("relationships", {})
    if not relationships:
        return "Relationships: nobody notable in this neighborhood yet."

    parts = []
    for other_name, relationship in relationships.items():
        parts.append(f"{other_name} is your {relationship}")
    return "Relationships: " + "; ".join(parts) + "."


def maybe_form_reflection(name):
    """Every ~5 events, form a one-line reflection that colors future reactions."""
    with _lock:
        _character_reflections[name]["event_count"] += 1
        count = _character_reflections[name]["event_count"]
        if count % 5 != 0 or count == 0:
            return _character_reflections[name]["text"]

        memories = list(_character_memories[name])
        if not memories:
            return ""

        templates = [
            "I keep noticing the street is changing. Something's different.",
            "Lately I've been paying closer attention to what people say around here.",
            "I can't shake the feeling that this block isn't what it used to be.",
            "Every day I notice something new. This neighborhood has layers.",
            "I'm starting to see patterns. Maybe I'm overthinking it.",
            "The more I watch, the less I understand. But I can't stop watching.",
            "Something about today felt different. I'll remember this.",
            "I've been thinking about what happened. It changed something in me.",
        ]

        _character_reflections[name]["text"] = random.choice(templates)
        return _character_reflections[name]["text"]


def get_reflection(name):
    with _lock:
        return _character_reflections[name]["text"]
