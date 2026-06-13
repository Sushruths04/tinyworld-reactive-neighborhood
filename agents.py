import os
import random
import concurrent.futures
import json
import characters as chars
import unpredictability

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MODAL_REACT_URL = os.environ.get(
    "MODAL_REACT_URL",
    "https://mitvho09--tinyworld-inference-react-endpoint.modal.run",
)

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


def _build_mood_context(mood):
    mood_notes = {
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
    return mood_notes.get(mood, "")


def build_agent_prompt(character, event, mood, memory, relationships):
    seed = random.choice(unpredictability.SURPRISE_SEEDS)

    memory_str = ""
    if memory:
        memory_str = "Your recent memories: " + "; ".join(memory[-3:]) + "."

    reflection = unpredictability.get_reflection(character["name"])
    reflection_str = ""
    if reflection:
        reflection_str = f"Inner reflection: {reflection}"

    persona = (
        f"You are {character['name']}, a {character['age']}-year-old {character['job']}. "
        f"Traits: {', '.join(character['traits'])}. "
        f"Backstory: {character['backstory']}. "
        f"{relationships} "
        f"{memory_str} "
        f"{reflection_str}"
    )

    prompt = (
        f"{persona}\n\n"
        f"Current mood: {mood}. {_build_mood_context(mood)}\n\n"
        f"Event that just happened: {event}\n\n"
        f"Respond in 2-3 sentences. Stay in character. Reference your mood and memories naturally. "
        f"{seed} "
        f"DO NOT be predictable. NO narration — just your direct reaction."
    )
    return prompt


def _mock_react(character, event, mood):
    char_name = character["name"]
    mood_reactions = MOCK_REACTIONS.get(char_name, MOCK_REACTIONS["Marta Voss"])
    pool = mood_reactions.get(mood, mood_reactions.get("bored", ["Hmm. Interesting."]))

    text = random.choice(pool)

    drama = random.uniform(0.2, 0.95)
    exclamations = text.count("!")
    caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
    drama = min(1.0, drama + exclamations * 0.05 + caps_words * 0.05)

    return {
        "name": char_name,
        "job": character["job"],
        "mood": mood,
        "model": character["model"],
        "text": text,
        "drama": round(drama, 3),
    }


def _real_react(character, event, mood, memory, relationships):
    prompt = build_agent_prompt(character, event, mood, memory, relationships)

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
            rx = reactions[0]
            text = rx["text"]

            drama = random.uniform(0.3, 0.8)
            exclamations = text.count("!")
            caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
            drama = min(1.0, drama + exclamations * 0.05 + caps_words * 0.05)

            return {
                "name": character["name"],
                "job": character["job"],
                "mood": mood,
                "model": character["model"],
                "text": text,
                "drama": round(drama, 3),
            }
        else:
            print(f"[agents] Modal returned error for {character['name']}")
            return _mock_react(character, event, mood)

    except Exception as e:
        print(f"[agents] Modal call failed for {character['name']}: {e}")
        return _mock_react(character, event, mood)


def _react_one(character, event):
    mood = unpredictability.reroll_mood(character["name"])
    memory = unpredictability.get_recent_memories(character["name"])
    relationships = unpredictability.format_relationships(character)

    if MOCK:
        result = _mock_react(character, event, mood)
    else:
        result = _real_react(character, event, mood, memory, relationships)

    unpredictability.update_memory(character["name"], event, result["text"])
    return result


def react(event: str) -> list:
    if MOCK:
        return _react_mock(event)
    else:
        return _react_modal(event)


def _react_mock(event: str) -> list:
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_react_one, char, event): char
            for char in chars.CHARACTERS
        }
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                char = futures[future]
                print(f"[agents] error for {char['name']}: {e}")
                mood = unpredictability.get_mood(char["name"])
                results.append({
                    "name": char["name"],
                    "job": char["job"],
                    "mood": mood,
                    "model": char["model"],
                    "text": f"[Something went wrong, but {char['name']} is still thinking...]",
                    "drama": 0.1,
                })

    order = {c["name"]: i for i, c in enumerate(chars.CHARACTERS)}
    results.sort(key=lambda r: order.get(r["name"], 99))
    return results


def _react_modal(event: str) -> list:
    import httpx

    chars_by_model = {}
    for char in chars.CHARACTERS:
        model = char["model"]
        if model not in chars_by_model:
            chars_by_model[model] = []
        chars_by_model[model].append(char)

    all_results = []

    for model_id, model_chars in chars_by_model.items():
        prompts = {}
        for char in model_chars:
            mood = unpredictability.reroll_mood(char["name"])
            memory = unpredictability.get_recent_memories(char["name"])
            relationships = unpredictability.format_relationships(char)
            prompt = build_agent_prompt(char, event, mood, memory, relationships)
            prompts[char["name"]] = prompt

        try:
            payload = {
                "event": event,
                "characters": model_chars,
                "prompts": prompts,
            }

            with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                resp = client.post(MODAL_REACT_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()

            modal_reactions = {r["name"]: r for r in data.get("reactions", [])}

            for char in model_chars:
                mood = unpredictability.get_mood(char["name"])
                rx = modal_reactions.get(char["name"], {})

                if rx and not rx.get("error") and len(rx.get("text", "")) > 10:
                    text = rx["text"]
                else:
                    print(f"[agents] Modal failed for {char['name']}, using mock")
                    mock_result = _mock_react(char, event, mood)
                    text = mock_result["text"]

                drama = random.uniform(0.3, 0.8)
                exclamations = text.count("!")
                caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
                drama = min(1.0, drama + exclamations * 0.05 + caps_words * 0.05)

                all_results.append({
                    "name": char["name"],
                    "job": char["job"],
                    "mood": mood,
                    "model": char["model"],
                    "text": text,
                    "drama": round(drama, 3),
                })

                unpredictability.update_memory(char["name"], event, text)

        except Exception as e:
            print(f"[agents] Modal batch failed for model {model_id}: {e}")
            for char in model_chars:
                mood = unpredictability.reroll_mood(char["name"])
                result = _mock_react(char, event, mood)
                all_results.append(result)
                unpredictability.update_memory(char["name"], event, result["text"])

    order = {c["name"]: i for i, c in enumerate(chars.CHARACTERS)}
    all_results.sort(key=lambda r: order.get(r["name"], 99))
    return all_results


def generate_followup(reactions, event):
    """Generate a short follow-up beat referencing a prior reaction (probabilistic)."""
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
    reactions = react("A mysterious glowing object lands in the park")
    for r in reactions:
        print(f"{r['name']} | {r['mood']} | {r['text']}")
    followup = generate_followup(reactions, "A mysterious glowing object lands in the park")
    if followup:
        print(f"\n[FOLLOWUP] {followup['text']}")
