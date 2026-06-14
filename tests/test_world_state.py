import world_state
from worlds import get_world


def test_tick_advances_day_after_midnight():
    world = get_world("maple_street")
    state = world_state.reset_world(world["id"])
    world_state.init_cast(world)
    state["game_time"] = 23.5
    world_state.tick(world, hours=1.0, force=True)
    day, hour, _ = world_state.get_game_time(world["id"])
    assert day == 2
    assert hour == 0.5


def test_pause_blocks_non_forced_tick():
    world = get_world("maple_street")
    world_state.reset_world(world["id"])
    world_state.init_cast(world)
    world_state.set_paused(world["id"], True)
    world_state.tick(world, hours=1.0)
    assert world_state.get_game_time(world["id"])[1] == 7.0
    world_state.tick(world, hours=1.0, force=True)
    assert world_state.get_game_time(world["id"])[1] == 8.0
