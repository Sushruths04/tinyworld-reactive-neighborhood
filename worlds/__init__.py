from worlds.maple_street import WORLD as MAPLE_STREET
from worlds.starhaven import WORLD as STARHAVEN
from worlds.old_town import WORLD as OLD_TOWN

WORLDS = {
    "maple_street": MAPLE_STREET,
    "starhaven": STARHAVEN,
    "old_town": OLD_TOWN,
}


def get_world(world_id):
    return WORLDS.get(world_id)


def list_worlds():
    return [
        {"id": wid, "name": w["name"], "theme": w["theme"]}
        for wid, w in WORLDS.items()
    ]
