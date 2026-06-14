import validate_worlds
from worlds import WORLDS


def test_world_registry_is_locked_to_two_worlds():
    assert set(WORLDS) == {"maple_street", "riverside_campus"}


def test_validator_passes():
    assert validate_worlds.main() == 0
