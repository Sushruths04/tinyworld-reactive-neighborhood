import json
import os
import random
import re
import time
from dataclasses import dataclass, field


MOODS = [
    "happy", "stressed", "bored", "excited", "hungry",
    "tired", "nostalgic", "curious", "proud", "embarrassed",
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

MODAL_REACT_URL = os.environ.get(
    "MODAL_REACT_URL",
    "https://mitvho09--tinyworld-inference-react-endpoint.modal.run",
)


@dataclass
class Decision:
    think: str
    say: str
    action: str
    goto: str
    mood: str
    need_deltas: dict = field(default_factory=dict)
    degraded: bool = False
    error: bool = False
    warning: str = ""
    raw: str = ""
    latency: float | None = None


def allowed_hotspots(world):
    return list(((world.get("board", {}) or {}).get("hotspots_tile") or {}).keys())


def current_activity(character, world, position):
    activities = (world.get("board", {}) or {}).get("activities", {})
    if character["name"] in activities:
        return activities[character["name"]].get("label", "going about their day")
    if position:
        return f"near {position.replace('_', ' ')}"
    return "going about their day"


def build_decision_prompt(character, event, mood, memory, relationships, world, position=None, needs=None):
    first = character["name"].split()[0]
    hotspots = allowed_hotspots(world)
    needs = needs or {"energy": 50, "hunger": 50, "social": 50}
    activity = current_activity(character, world, position)
    memory_text = "; ".join(memory[-4:]) if memory else "nothing recent"
    seed = random.choice(SURPRISE_SEEDS)

    return f"""You are controlling one TinyWorld character.

Persona:
- Name: {character['name']}
- Age/job: {character['age']}, {character['job']}
- Traits: {', '.join(character.get('traits', []))}
- Backstory: {character.get('backstory', '')}
- Relationships: {relationships}

Current state:
- Mood before deciding: {mood}
- Current place: {position or character.get('home', 'unknown')}
- Current activity: {activity}
- Needs: energy={needs.get('energy', 50)}, hunger={needs.get('hunger', 50)}, social={needs.get('social', 50)}
- Recent memory: {memory_text}

Allowed goto values: {', '.join(hotspots)}, stay
Triggering input: {event}
Surprise instruction: {seed}

Return ONLY strict JSON with exactly these keys:
{{
  "think": "one short private thought, max 120 chars",
  "say": "what {first} says aloud, 1-2 short sentences, in-character",
  "action": "a concrete verb phrase describing what {first} does",
  "goto": "one allowed goto value or stay",
  "mood": "one of: {', '.join(MOODS)}",
  "need_deltas": {{"energy": 0, "hunger": 0, "social": 0}}
}}

No markdown, no commentary, no labels outside the JSON object."""


def decide_real(character, event, mood, memory, relationships, world, position=None, needs=None):
    prompt = build_decision_prompt(character, event, mood, memory, relationships, world, position, needs)
    raw, latency = _call_modal(character, event, prompt)
    decision = parse_decision(raw, world, previous_mood=mood)
    decision.latency = latency
    if decision.degraded:
        retry_prompt = prompt + "\n\nYour previous response was invalid. Return ONLY the JSON object."
        raw_retry, retry_latency = _call_modal(character, event, retry_prompt, timeout=45.0)
        decision = parse_decision(raw_retry, world, previous_mood=mood)
        decision.latency = retry_latency
    return decision


def mock_decision(character, event, mood, world):
    hotspots = allowed_hotspots(world)
    goto = _event_goto(event, hotspots)
    chosen_mood = random.choice(MOODS)
    first = character["name"].split()[0]
    action = _mock_action(character, goto)
    templates = [
        f"{first} says this feels {chosen_mood}, but I'm going to {action}.",
        f"I don't love surprises like this. I'll {action} and see what is really going on.",
        f"This is exactly the sort of thing my day was missing. I'm going to {action}.",
    ]
    return Decision(
        think=f"{first} connects the event to their role.",
        say=random.choice(templates),
        action=action,
        goto=goto,
        mood=chosen_mood,
        need_deltas={
            "energy": random.randint(-8, 4),
            "hunger": random.randint(-3, 6),
            "social": random.randint(-4, 8),
        },
    )


def parse_decision(raw, world, previous_mood="curious"):
    data = _extract_json(raw)
    if data is None:
        return _safe_decision(previous_mood, "malformed JSON", raw)

    hotspots = allowed_hotspots(world)
    think = _limit(_clean_text(data.get("think", "")), 120)
    say = _limit(_clean_dialogue(data.get("say", "")), 220)
    action = _limit(_clean_text(data.get("action", "")), 160)
    goto = _clean_goto(data.get("goto", "stay"), hotspots)
    mood = data.get("mood", previous_mood)
    if mood not in MOODS:
        mood = previous_mood if previous_mood in MOODS else "curious"

    deltas = data.get("need_deltas", {})
    if not isinstance(deltas, dict):
        deltas = {}
    need_deltas = {
        "energy": _clamp_int(deltas.get("energy", 0), -25, 25),
        "hunger": _clamp_int(deltas.get("hunger", 0), -25, 25),
        "social": _clamp_int(deltas.get("social", 0), -25, 25),
    }

    if not say:
        return _safe_decision(mood, "empty dialogue after cleaning", raw)
    if not action:
        action = "stay alert and watch what happens next"
    return Decision(think, say, action, goto, mood, need_deltas, raw=raw)


def _call_modal(character, event, prompt, timeout=180.0):
    import httpx

    payload = {
        "event": event,
        "characters": [character],
        "prompts": {character["name"]: prompt},
    }
    started = time.time()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.post(MODAL_REACT_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    reactions = data.get("reactions", [])
    if not reactions or reactions[0].get("error"):
        message = reactions[0].get("text", "model unreachable") if reactions else "model unreachable"
        raise RuntimeError(message)
    return reactions[0].get("text", ""), round(time.time() - started, 2)


def _extract_json(raw):
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _clean_goto(value, hotspots):
    goto = str(value or "stay").strip().lower().replace(" ", "_")
    goto = re.sub(r"[^a-z0-9_]", "", goto)
    if goto == "stay":
        return "stay"
    return goto if goto in hotspots else "stay"


def _safe_decision(mood, warning, raw):
    return Decision(
        think="The model output could not be used.",
        say="I need a second before I can make sense of that.",
        action="stay put and reassess",
        goto="stay",
        mood=mood if mood in MOODS else "curious",
        need_deltas={"energy": 0, "hunger": 0, "social": 0},
        degraded=True,
        warning=warning,
        raw=raw or "",
    )


def _clean_text(value):
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _clean_dialogue(value):
    text = _clean_text(value)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\*[^*]*\*", "", text)
    text = re.sub(r"^(say|do|think|goto)\s*:\s*", "", text, flags=re.IGNORECASE)
    meta = re.compile(r"(as an ai|the prompt|return only json|1-2 sentences|in character)", re.IGNORECASE)
    parts = [p.strip(" \"'") for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    keep = [p for p in parts if not meta.search(p)]
    return " ".join(keep[:2]).strip()


def _limit(text, max_chars):
    text = _clean_text(text)
    return text[:max_chars].rstrip()


def _clamp_int(value, low, high):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    return max(low, min(high, value))


def _event_goto(event, hotspots):
    e = event.lower()
    rules = [
        (("clinic", "hurt", "injur", "sick", "emergency", "storm"), "nia_clinic"),
        (("school", "student", "class", "teacher"), "school"),
        (("cafe", "café", "coffee", "food", "hungry"), "cafe"),
        (("park", "tree", "glow", "object", "cat", "mural"), "park"),
        (("office", "city", "budget", "permit", "power"), "priya_office"),
        (("home", "rest"), "marta_home"),
    ]
    for words, goto in rules:
        if any(word in e for word in words) and goto in hotspots:
            return goto
    return "square" if "square" in hotspots else "stay"


def _mock_action(character, goto):
    place = goto.replace("_", " ")
    role = character.get("job", "neighbor")
    return random.choice([
        f"go to {place} and check the situation",
        f"use my {role} instincts at {place}",
        f"head for {place} before rumors outrun the facts",
    ])
