import os
import random
import re
import concurrent.futures
import world_state
from worlds import get_world

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MODAL_REACT_URL = os.environ.get(
    "MODAL_REACT_URL",
    "https://mitvho09--tinyworld-inference-react-endpoint.modal.run",
)

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

MOOD_CONTEXT = {
    "happy": "You are in a good mood. Let that warmth show.",
    "stressed": "You are stressed and overwhelmed. It colors your view.",
    "bored": "You are bored. Nothing impresses you.",
    "excited": "You are buzzing with excitement.",
    "hungry": "You are hungry and losing patience.",
    "tired": "You are exhausted. Everything is too much effort.",
    "nostalgic": "You are nostalgic. The past feels more real.",
    "curious": "You are intensely curious. You want answers.",
    "proud": "You are proud. This is your turf.",
    "embarrassed": "You are embarrassed. You hope nobody noticed.",
}

GENERIC_MOCK = {
    "happy": ["Honestly? I love this. Best thing to happen here in ages.", "Oh, this is wonderful. Count me in!"],
    "stressed": ["This is exactly what I was afraid of. We need a plan, now.", "Okay, okay — everybody stay calm. Mostly me."],
    "bored": ["Huh. Neat, I guess. Wake me if it gets interesting.", "Seen weirder. Slightly."],
    "excited": ["No way! This is HUGE, we have to do something!", "I have been WAITING for something like this!"],
    "hungry": ["Can we deal with this after I eat? Just asking.", "Great, drama on an empty stomach."],
    "tired": ["I do not have the energy for this today.", "Can someone else handle it? I'm wiped."],
    "nostalgic": ["This takes me back. Funny how things come around.", "Reminds me of the old days, before all... this."],
    "curious": ["Wait, how does that even work? I need to know more.", "Fascinating. Let me get a closer look."],
    "proud": ["Stand back — I've got this handled.", "Finally, a chance to show what I can do."],
    "embarrassed": ["Oh no. Please tell me nobody saw that.", "I'm just going to pretend that didn't happen."],
}

MOCK_REACTIONS = {
    "Marta Voss": {
        "happy": [
            "Well, that's a pleasant surprise. I could use more days like this around here.",
            "Ha! Finally something good happens. Don't tell anyone I said that.",
        ],
        "stressed": [
            "Oh great, just what I needed. As if this block wasn't chaotic enough already.",
            "I'm going to need a moment. Or a time machine to 1987.",
        ],
        "bored": [
            "Huh. That's something, I guess. Wake me when it gets interesting.",
            "Back in my day, we had real excitement. This is... fine.",
        ],
        "excited": [
            "Now THIS is what I've been waiting for! Reminds me of the great power outage of '09!",
            "I've been watching this neighborhood for forty years and THIS is the day!",
        ],
        "hungry": [
            "Nice, but can we talk about lunch first? I skipped my tea.",
            "That's all well and good, but I haven't had a decent scone since Tuesday.",
        ],
        "tired": [
            "Can this wait? I barely slept last night thanks to Jay's delivery bike.",
            "*yawn* That's... very... I need my afternoon nap.",
        ],
        "nostalgic": [
            "This reminds me of something from '83. Similar energy, different decade.",
            "You know, we had something like this once before. Not quite the same though.",
        ],
        "curious": [
            "Wait, hold on. Tell me more. What exactly did you see?",
            "Something doesn't add up. I've been watching this street for decades and I notice things.",
        ],
        "proud": [
            "I've been saying this block would get noticed. Called it years ago.",
            "This is exactly the kind of thing I've seen coming. You're all welcome.",
        ],
        "embarrassed": [
            "Oh no. Please tell me nobody saw me react to that.",
            "I... uh... let's just pretend that didn't happen.",
        ],
    },
    "Jay Park": {
        "happy": [
            "Ha! Finally! I KNEW something good was coming today! My luck's turning around!",
            "This is amazing! I'm already texting everyone about it!",
        ],
        "stressed": [
            "Oh no. Oh no no no. I literally cannot deal with this right now!",
            "My schedule is already packed and NOW this happens?!",
        ],
        "bored": [
            "That's... cool I guess? I've seen more exciting delivery routes.",
            "Wake me when something actually interesting happens. I'm going for a ride.",
        ],
        "excited": [
            "WAIT WAIT WAIT — did you SEE that?! This is HUGE! I'm already on it!",
            "I KNEW something like this would happen! My instincts are NEVER wrong!",
        ],
        "hungry": [
            "Cool cool cool, but has anyone seen the pizza truck? I'm STARVING.",
            "I'd be more excited if I hadn't skipped lunch for three deliveries.",
        ],
        "tired": [
            "Mmhmm. Very cool. *stares into distance* I delivered twelve orders today.",
            "Can this wait? My legs are literally trembling.",
        ],
        "nostalgic": [
            "This gives me the same vibe as that time I found twenty bucks in a taxi. Good memories.",
            "You know, this reminds me of my first week on the job. Good times.",
        ],
        "curious": [
            "Wait, what?! Tell me EVERYTHING. I need details!",
            "Something's up. I ride through here every day and I notice things.",
        ],
        "proud": [
            "Ha! I've been saying this neighborhood was special! Who's laughing now?",
            "I literally called this. Check my texts from last week.",
        ],
        "embarrassed": [
            "Oh god. Please tell me I didn't just yell that out loud.",
            "I'm going to ride away now. Very fast. In the opposite direction.",
        ],
    },
    "Nia Okafor": {
        "happy": [
            "Well, that's a nice change of pace. I could get used to this.",
            "Good. We deserve something good around here for once.",
        ],
        "stressed": [
            "Okay, deep breaths. I've handled worse in the ambulance. This is fine.",
            "Of course this happens on my day off. Of course it does.",
        ],
        "bored": [
            "Fascinating. Truly. *checks watch* I've seen more action at a stop sign.",
            "My enthusiasm is immeasurable. *yawn*",
        ],
        "excited": [
            "Now THIS is interesting! Finally, something that gets the blood pumping!",
            "Oh, this is good. This is REALLY good. I'm alert now.",
        ],
        "hungry": [
            "I've got one eye on this and one eye on the clock. Shift starts in an hour and I need food.",
            "Cool, but I'm about to pass out from low blood sugar. Priorities.",
        ],
        "tired": [
            "I've seen worse. Much worse. But I'd rather be sleeping right now.",
            "Can we... handle this efficiently? I worked a double shift.",
        ],
        "nostalgic": [
            "This reminds me of my first month on the job. Similar chaos, different faces.",
            "You know, we had something like this at the hospital once. Long story.",
        ],
        "curious": [
            "Hold on. What exactly happened? I need the facts before I react.",
            "Something's not right here. I read situations for a living and this is off.",
        ],
        "proud": [
            "This neighborhood doesn't get enough credit. But I've always known.",
            "I've been protecting this block for years. Nice to see others noticing.",
        ],
        "embarrassed": [
            "I... that was unprofessional. Let's move on.",
            "Nobody saw that. Nobody. *straightens uniform*",
        ],
    },
    "Luca Bell": {
        "happy": [
            "OH MY GOSH THIS IS THE BEST DAY EVER! I need to document everything!",
            "I KNEW something amazing would happen! My notebook predicted this!",
        ],
        "stressed": [
            "This is TERRIBLE! This is the worst thing that has EVER happened on this block!",
            "I'm writing this down as a DISASTER. My notebook needs a new chapter!",
        ],
        "bored": [
            "That's it? I expected more. My notebook is disappointed.",
            "I've been waiting for something cool and THIS is what we get?",
        ],
        "excited": [
            "THIS IS THE MOST IMPORTANT THING THAT HAS EVER HAPPENED! I'M SHAKING!",
            "I need to record this IMMEDIATELY! Future historians will thank me!",
        ],
        "hungry": [
            "I'd be more excited but I skipped lunch to wait for something cool to happen.",
            "This is amazing but I'm literally starving. Can we celebrate with snacks?",
        ],
        "tired": [
            "I want to care about this but my eyes won't stay open.",
            "Can... can this wait? I was up until 2am researching neighborhood legends.",
        ],
        "nostalgic": [
            "This reminds me of the time I found that old map in Marta's shop! Similar vibes!",
            "You know, this is exactly the kind of thing I've been writing about for months!",
        ],
        "curious": [
            "Wait WHAT?! I need to investigate this IMMEDIATELY! Where's my notebook?!",
            "This is suspicious. Very suspicious. I'm going to get to the bottom of this!",
        ],
        "proud": [
            "I TOLD everyone something amazing would happen here! Check my notebook!",
            "This is proof! This neighborhood is SPECIAL and I've been saying it all along!",
        ],
        "embarrassed": [
            "I just screamed really loud didn't I? Please tell me nobody heard that.",
            "I'm going to go hide in my room now. For several days.",
        ],
    },
    "Priya Raman": {
        "happy": [
            "Well, this is a welcome surprise. I'll add it to the positive column.",
            "Good. This block could use some good news for a change.",
        ],
        "stressed": [
            "First, let's assess the situation. Second, let's make a plan. Third, PANIC.",
            "I'm making a list. Of everything that could go wrong. It's a long list.",
        ],
        "bored": [
            "I'll believe it when I see it. Until then, I have zoning reports to review.",
            "Everyone calm down. This probably isn't what it seems.",
        ],
        "excited": [
            "Okay, I'll admit it — this is genuinely exciting. I'm making an exception to my skepticism.",
            "This changes the whole dynamic of the block! I need to recalculate everything!",
        ],
        "hungry": [
            "I hate to admit it, but I'm too hungry to think clearly right now.",
            "Can we table this discussion until after lunch? I'm not functioning.",
        ],
        "tired": [
            "I've got my eye on this, but I'm too exhausted to process it fully.",
            "This is significant, but I need coffee before I can formulate a proper response.",
        ],
        "nostalgic": [
            "There's something beautiful about chaos, isn't there? Even organized chaos.",
            "I hate to admit it, but this is kind of poetic. In a messy sort of way.",
        ],
        "curious": [
            "Something doesn't add up here. I'm going to look into this officially.",
            "I need more data before I form an opinion. This feels... incomplete.",
        ],
        "proud": [
            "I've spent years trying to improve this block. Nice to see it getting attention.",
            "This is exactly the kind of thing I've been working toward. You're welcome.",
        ],
        "embarrassed": [
            "I just got excited about something unprofessional didn't I? Let's never speak of this.",
            "My carefully maintained composure just cracked. Wonderful.",
        ],
    },
}

MOVEMENT_HINTS = [
    "If you'd naturally move somewhere during this event, end your reaction with [GOTO: hotspot_name].",
    "If this event would make you walk to a different part of the neighborhood, end with [GOTO: hotspot_name].",
    "Stay put unless the event strongly draws you somewhere else. If you move, end with [GOTO: hotspot_name].",
]

HOTSPOT_KEYS = [
    "marta_home", "cafe", "park", "square", "jay_home",
    "school", "nia_clinic", "priya_office",
]


def _build_mood_context(mood):
    return MOOD_CONTEXT.get(mood, "")


def _hotspots(world):
    """Destinations a character can choose. Prefer board tiles (what the app maps
    and the renderer draws); fall back to the legacy top-level dict. Robust for
    every world — starhaven/old_town only define board['hotspots_tile']."""
    return (world.get("board", {}) or {}).get("hotspots_tile") or world.get("hotspots") or {}


def build_agent_prompt(character, event, mood, memory, relationships, world):
    seed = random.choice(SURPRISE_SEEDS)
    movement = random.choice(MOVEMENT_HINTS)

    memory_str = ""
    if memory:
        memory_str = "Your recent memories: " + "; ".join(memory[-4:]) + "."

    reflection = world_state.get_reflection(world["id"], character["name"])
    reflection_str = ""
    if reflection:
        reflection_str = f"Inner reflection: {reflection}"

    hotspots = ", ".join(_hotspots(world).keys())

    persona = (
        f"You are {character['name']}, a {character['age']}-year-old {character['job']}. "
        f"Traits: {', '.join(character['traits'])}. "
        f"Backstory: {character['backstory']}. "
        f"Catchphrase style: {character.get('catchphrase_hint', '')}. "
        f"{relationships} "
        f"{memory_str} "
        f"{reflection_str}"
    )

    first = character["name"].split()[0]
    prompt = (
        f"{persona}\n\n"
        f"Your mood right now: {mood}. {_build_mood_context(mood)}\n\n"
        f"Something just happened on your street: \"{event}\"\n\n"
        f"React the way {first} truly would. In 1 to 2 short sentences, speak OUT LOUD in first person "
        f"— your own voice — showing you understood what happened and what you mean to do about it. "
        f"{seed} "
        f"Speak ONLY as {first}: no narration, no stage directions, no notes to yourself, no labels, no quotation marks."
    )
    return prompt


# scratch / meta lines a weak model leaks instead of staying in character
_META_RE = re.compile(
    r"^(let me\b|i need to\b|i should\b|i'll (incorporate|write|make|ensure)|now,?\s*i\b|"
    r"but the format\b|i think that works\b|first,?\s*i\b|okay,?\s*(so|let)\b|here('s| is)\b|"
    r"in the (do|think|say)\b|for (the )?(say|do|think)\b|the format\b|as an ai\b|sure,?\s|note:)",
    re.IGNORECASE,
)

# task-referential phrases that mean the model is talking about the assignment, not the street
_META_CONTAINS = re.compile(
    r"(sentence|i'?ll count|let'?s (write|count|ensure)|1 to 2|the format|in character|"
    r"the prompt|stage direction|first sentence|i (will|'?ll) (say|write))",
    re.IGNORECASE,
)


def _clean_line(raw):
    """Pull a clean, in-character spoken line out of a messy small-model reply."""
    raw = (raw or "").strip()
    m = re.search(r"say\s*:\s*(.+)", raw, re.IGNORECASE)      # honor old SAY: format if used
    cand = m.group(1).strip() if m else raw
    cand = re.sub(r"\b(think|do|say|goto)\s*:\s*", " ", cand, flags=re.IGNORECASE)
    cand = re.sub(r"\[[^\]]*\]", "", cand)                    # [GOTO: ...] / brackets
    cand = re.sub(r"\*[^*]*\*", "", cand)                     # *stage directions*
    cand = cand.replace("\n", " ").strip()
    parts = re.split(r"(?<=[.!?])\s+", cand)
    keep = [p.strip(" \"'") for p in parts
            if p.strip() and not _META_RE.match(p.strip()) and not _META_CONTAINS.search(p)]
    # empty => nothing in-character survived; caller falls back to a persona line
    return " ".join(keep[:2]).strip(" \"'")


def _parse_goto(text):
    match = re.search(r'\[GOTO:\s*(\w+)\]', text)
    if match:
        hotspot = match.group(1)
        clean_text = re.sub(r'\[GOTO:\s*\w+\]', '', text).strip()
        if hotspot in HOTSPOT_KEYS:
            return clean_text, hotspot
        return clean_text, None
    return text, None


def _field(text, key):
    m = re.search(rf'^\s*{key}\s*:\s*(.+?)\s*$', text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_structured(raw, world):
    """Pull THINK / DO / SAY / GOTO out of a reasoning reply. Falls back to the
    older [GOTO] / free-text shape so a model that ignores the format still works."""
    think = _field(raw, "THINK")
    do = _field(raw, "DO")
    say = _field(raw, "SAY")
    goto_raw = _field(raw, "GOTO")

    goto = None
    keys = list(_hotspots(world).keys())
    if goto_raw:
        cand = re.sub(r'[^a-z_]', '', goto_raw.lower().replace(" ", "_"))
        if cand in keys:
            goto = cand
        else:
            for k in keys:
                if k in cand or cand in k:
                    goto = k
                    break

    if not say:
        # model didn't follow the format — treat the whole thing as the spoken line
        say, legacy_goto = _parse_goto(raw.strip())
        goto = goto or legacy_goto

    # trim a stray DO that leaked into the spoken line
    say = re.sub(r'^(THINK|DO|SAY|GOTO)\s*:\s*', '', say, flags=re.IGNORECASE).strip()
    return think, do, say or raw.strip(), goto


def _compute_drama(text):
    drama = random.uniform(0.2, 0.9)
    exclamations = text.count("!")
    caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
    drama = min(1.0, drama + exclamations * 0.05 + caps_words * 0.05)
    return round(drama, 3)


def _compute_vibe_delta(mood):
    base = {"energy": 0.0, "social": 0.0}
    mood_energy = {
        "happy": 0.08, "excited": 0.12, "proud": 0.06, "curious": 0.04,
        "stressed": -0.1, "bored": -0.08, "tired": -0.15, "hungry": -0.05,
        "nostalgic": 0.02, "embarrassed": -0.03,
    }
    mood_social = {
        "happy": 0.1, "excited": 0.08, "curious": 0.06, "proud": 0.02,
        "nostalgic": 0.04, "stressed": -0.06, "bored": -0.1, "tired": -0.08,
        "hungry": -0.04, "embarrassed": -0.05,
    }
    base["energy"] = mood_energy.get(mood, 0.0) + random.uniform(-0.02, 0.02)
    base["social"] = mood_social.get(mood, 0.0) + random.uniform(-0.02, 0.02)
    return base


def _compute_affinity_deltas(name, character, mood):
    deltas = {}
    for other_name, rel in character.get("relationships", {}).items():
        if rel == "friend":
            deltas[other_name] = random.uniform(0.01, 0.04)
        elif rel == "rival":
            deltas[other_name] = random.uniform(-0.04, -0.01)
        elif rel == "crush":
            deltas[other_name] = random.uniform(0.02, 0.06)
        elif rel == "family":
            deltas[other_name] = random.uniform(0.01, 0.03)
        if mood in ("stressed", "angry"):
            deltas[other_name] = deltas.get(other_name, 0) - 0.02
        elif mood in ("happy", "excited"):
            deltas[other_name] = deltas.get(other_name, 0) + 0.01
    return deltas


# keyword -> where a sensible person would head to deal with that kind of situation
_EVENT_HOTSPOT = [
    (("power", "outage", "lights", "electric"), "priya_office"),
    (("school", "kids", "class", "student"), "school"),
    (("hurt", "injur", "accident", "sick", "fire", "emergency", "storm"), "nia_clinic"),
    (("food", "truck", "hungry", "coffee", "cafe", "café"), "cafe"),
    (("park", "tree", "object", "glow", "mural", "cat", "kitten", "animal"), "park"),
    (("meeting", "everyone", "gather", "crowd", "news", "vote"), "square"),
]


def _mock_brain(character, event, world):
    """Cheap stand-in for real reasoning: a relevant destination + a concrete action,
    so even the offline demo shows characters engaging the situation, not just emoting."""
    e = event.lower()
    hs = _hotspots(world)
    goto = None
    for keys, spot in _EVENT_HOTSPOT:
        if any(k in e for k in keys) and spot in hs:
            goto = spot
            break
    if not goto:
        goto = "square" if "square" in hs else (random.choice(list(hs.keys())) if hs else None)
    # spread the cast out: about half deal with it on their own turf instead of all piling onto one spot
    home = character.get("home")
    if home in hs and random.random() < 0.5:
        goto = home
    job = character.get("job", "neighbor")
    action = random.choice([
        f"head to the {goto.replace('_', ' ')} to see it firsthand",
        f"go to the {goto.replace('_', ' ')} and do something about it",
        f"use what they know as a {job} to help",
        f"rally a neighbor and act on it together",
        f"check on the people most affected first",
    ])
    understanding = "This changes things on the block — better to deal with it than ignore it."
    return understanding, action, goto


def _mock_react(character, event, mood, world):
    char_name = character["name"]
    mood_reactions = MOCK_REACTIONS.get(char_name, GENERIC_MOCK)
    pool = mood_reactions.get(mood, mood_reactions.get("bored", ["Hmm. Interesting."]))

    text = random.choice(pool)
    drama = _compute_drama(text)

    text, goto = _parse_goto(text)
    understanding, action, brain_goto = _mock_brain(character, event, world)
    if not goto:
        goto = brain_goto

    return {
        "name": char_name,
        "mood": mood,
        "text": text,
        "understanding": understanding,
        "action": action,
        "model": character["model"],
        "drama": drama,
        "moved_to": goto,
        "vibe_delta": _compute_vibe_delta(mood),
        "affinity_deltas": _compute_affinity_deltas(char_name, character, mood),
    }


def _real_react(character, event, mood, memory, relationships, world):
    prompt = build_agent_prompt(character, event, mood, memory, relationships, world)

    try:
        import httpx

        payload = {
            "event": event,
            "characters": [character],
            "prompts": {character["name"]: prompt},
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(MODAL_REACT_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        reactions = data.get("reactions", [])
        if reactions and not reactions[0].get("error"):
            raw = reactions[0]["text"]
            text = _clean_line(raw)                       # real LLM dialogue, de-noised
            if len(text) < 4:                            # output was all task-meta — use a persona line
                return _mock_react(character, event, mood, world)
            # movement + action are decided by the engine so a weak model can't break them
            understanding, action, goto = _mock_brain(character, event, world)
            drama = _compute_drama(text + " " + action)

            return {
                "name": character["name"],
                "mood": mood,
                "text": text,
                "understanding": understanding,
                "action": action,
                "model": character["model"],
                "drama": drama,
                "moved_to": goto,
                "vibe_delta": _compute_vibe_delta(mood),
                "affinity_deltas": _compute_affinity_deltas(character["name"], character, mood),
            }
        else:
            return _mock_react(character, event, mood, world)

    except Exception as e:
        print(f"[agents] Modal call failed for {character['name']}: {e}")
        return _mock_react(character, event, mood, world)


def _react_one(character, event, world):
    wid = world["id"]
    mood = random.choice(MOODS)
    world_state.set_mood(wid, character["name"], mood)
    memory = world_state.get_memory(wid, character["name"])
    relationships = _format_relationships(character)

    if MOCK:
        result = _mock_react(character, event, mood, world)
    else:
        result = _real_react(character, event, mood, memory, relationships, world)

    # learn from what they DID, not just what they said, so future reactions build on it
    learned = result.get("action") or result["text"]
    world_state.add_memory(wid, character["name"], event, learned)
    return result


def _format_relationships(character):
    relationships = character.get("relationships", {})
    if not relationships:
        return "Relationships: nobody notable in this neighborhood yet."
    parts = [f"{other_name} is your {relationship}" for other_name, relationship in relationships.items()]
    return "Relationships: " + "; ".join(parts) + "."


def react(world_id, event, mode="solo"):
    world = get_world(world_id)
    if not world:
        raise ValueError(f"Unknown world: {world_id}")

    state = world_state.get_state(world_id)
    world_state.init_cast(world)
    world_state.increment_event(world_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_react_one, char, event, world): char
            for char in world["cast"]
        }
        reactions = []
        for future in concurrent.futures.as_completed(futures):
            try:
                reactions.append(future.result())
            except Exception as e:
                char = futures[future]
                print(f"[agents] error for {char['name']}: {e}")
                mood = world_state.get_mood(world_id, char["name"])
                reactions.append({
                    "name": char["name"],
                    "mood": mood,
                    "text": f"[Something went wrong, but {char['name']} is still thinking...]",
                    "model": char["model"],
                    "drama": 0.1,
                    "moved_to": None,
                    "vibe_delta": {"energy": 0, "social": 0},
                    "affinity_deltas": {},
                })

    order = {c["name"]: i for i, c in enumerate(world["cast"])}
    reactions.sort(key=lambda r: order.get(r["name"], 99))

    for r in reactions:
        world_state.apply_vibe_delta(world_id, r["name"], r["vibe_delta"])
        world_state.apply_affinity_delta(world_id, r["name"], r["affinity_deltas"])
        if r["moved_to"]:
            world_state.set_position(world_id, r["name"], r["moved_to"])

    town_delta = sum(r["vibe_delta"]["energy"] for r in reactions) / len(reactions)
    current_town = world_state.get_town_mood(world_id)
    world_state.set_town_mood(world_id, current_town + town_delta)

    for c in world["cast"]:
        if state["event_count"] % 3 == 0:
            world_state.maybe_form_reflection(world_id, c["name"])

    return {
        "reactions": reactions,
        "town_mood_delta": round(town_delta, 4),
    }


def generate_followup(reactions, event):
    if random.random() > 0.4:
        return None

    source = random.choice(reactions)
    others = [r for r in reactions if r["name"] != source["name"]]
    if not others:
        return None
    target = random.choice(others)

    templates = [
        f"Because {source['name']} reacted that way, {target['name']} quietly decides to keep an eye on them.",
        f"{target['name']} overheard {source['name']}'s reaction and can't stop thinking about it.",
        f"After hearing {source['name']}, {target['name']} changes their mind about the whole thing.",
        f"{target['name']} wonders if {source['name']} knows something they're not saying.",
        f"The look on {source['name']}'s face tells {target['name']} everything they need to know.",
        f"{target['name']} files away {source['name']}'s reaction for later. That was... telling.",
        f"While everyone else moves on, {target['name']} notices {source['name']} is still upset.",
        f"{target['name']} wants to ask {source['name']} what they really think, but not in front of everyone.",
    ]

    return {
        "type": "followup",
        "source": source["name"],
        "target": target["name"],
        "text": random.choice(templates),
        "mood": target["mood"],
    }


if __name__ == "__main__":
    from worlds import get_world
    w = get_world("maple_street")
    world_state.init_cast(w)
    result = react("maple_street", "A mysterious glowing object lands in the park")
    for r in result["reactions"]:
        print(f"{r['name']} | {r['mood']} | goto={r['moved_to']} | {r['text']}")
    print(f"\nTown mood delta: {result['town_mood_delta']}")
    followup = generate_followup(result["reactions"], "A mysterious glowing object lands in the park")
    if followup:
        print(f"\n[FOLLOWUP] {followup['text']}")
