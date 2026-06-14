from worlds.maple_street import WORLD as MAPLE_STREET
from worlds.riverside_campus import WORLD as RIVERSIDE_CAMPUS

WORLDS = {
    "maple_street": MAPLE_STREET,
    "riverside_campus": RIVERSIDE_CAMPUS,
}


def get_world(world_id):
    return WORLDS.get(world_id)


def list_worlds():
    return [
        {"id": wid, "name": w["name"], "theme": w["theme"]}
        for wid, w in WORLDS.items()
    ]
