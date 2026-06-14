import re


COMMAND_VERBS = {
    "go", "head", "walk", "run", "visit", "check", "rest", "help",
    "tell", "make", "ask", "send", "move", "bring", "look",
}

BASE_LOCATION_ALIASES = {
    "clinic": "nia_clinic",
    "hospital": "nia_clinic",
    "nurse": "nia_clinic",
    "cafe": "cafe",
    "café": "cafe",
    "coffee": "cafe",
    "school": "school",
    "class": "school",
    "park": "park",
    "fountain": "fountain",
    "square": "square",
    "plaza": "square",
    "office": "priya_office",
    "city hall": "priya_office",
    "shop": "shop",
    "store": "shop",
}


def classify(text, world):
    raw = (text or "").strip()
    if not raw:
        return {"type": "noop", "text": raw, "addressees": [], "instruction": "", "goto": None}
    if not re.search(r"[A-Za-z0-9]", raw):
        return {"type": "ambient", "text": raw, "addressees": [], "instruction": raw, "goto": None}

    cast = world.get("cast", [])
    names = _matched_names(raw, cast)
    lowered = raw.lower()
    looks_command = bool(names) and (
        _starts_with_name_command(lowered, names)
        or lowered.startswith("tell ")
        or lowered.startswith("make ")
        or lowered.startswith("ask ")
        or any(re.search(rf"\b{verb}\b", lowered) for verb in COMMAND_VERBS)
    )
    if looks_command:
        instruction = _strip_command_prefix(raw, names)
        goto = resolve_location(instruction, world, cast, names)
        return {
            "type": "directed_command",
            "text": raw,
            "addressees": names,
            "instruction": instruction,
            "goto": goto,
        }

    return {"type": "world_event", "text": raw, "addressees": [], "instruction": raw, "goto": None}


def resolve_location(text, world, cast=None, addressees=None):
    lowered = (text or "").lower()
    hotspots = ((world.get("board", {}) or {}).get("hotspots_tile") or {})

    if "home" in lowered and cast and addressees and len(addressees) == 1:
        char = next((c for c in cast if c["name"] == addressees[0]), None)
        home = char.get("home") if char else None
        if home in hotspots:
            return home

    aliases = dict(BASE_LOCATION_ALIASES)
    for key in hotspots:
        aliases[key] = key
        aliases[key.replace("_", " ")] = key
        aliases[key.replace("_", "")] = key

    for phrase, hotspot in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in lowered and hotspot in hotspots:
            return hotspot
    return None


def _matched_names(text, cast):
    lowered = text.lower()
    matches = []
    for char in cast:
        first = char["name"].split()[0].lower()
        if re.search(rf"\b{re.escape(first)}\b", lowered):
            matches.append(char["name"])
    return matches


def _starts_with_name_command(lowered, names):
    first_names = [name.split()[0].lower() for name in names]
    for first in first_names:
        if re.match(rf"^\s*{re.escape(first)}\s*[,:\-]\s*", lowered):
            return True
    return False


def _strip_command_prefix(text, names):
    instruction = text.strip()
    first_names = "|".join(re.escape(name.split()[0]) for name in names)
    patterns = [
        rf"^\s*(?:tell|ask|make|send)\s+(?:{first_names})\s+(?:to\s+)?",
        rf"^\s*(?:{first_names})\s*[,:\-]\s*",
    ]
    for pattern in patterns:
        instruction = re.sub(pattern, "", instruction, flags=re.IGNORECASE).strip()
    return instruction or text.strip()
