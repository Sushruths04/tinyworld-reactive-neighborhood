import world_state
from worlds import get_world


def test_student_schedule_at_0830():
    world = get_world("riverside_campus")
    world_state.reset_world(world["id"])
    world_state.init_cast(world)
    world_state.tick(world, hours=1.5, force=True)
    assert world_state.format_time(world_state.get_game_time(world["id"])[1]) == "08:30"
    assert world_state.get_position(world["id"], "Samir Patel") == "science_lab"
    assert world_state.get_activity(world["id"], "Samir Patel") == "classes and lab work"


def test_needs_drift_and_timeline_entries():
    world = get_world("maple_street")
    world_state.reset_world(world["id"])
    world_state.init_cast(world)
    before = world_state.get_needs(world["id"])["Luca Bell"].copy()
    world_state.tick(world, hours=1.0, force=True)
    after = world_state.get_needs(world["id"])["Luca Bell"]
    assert after != before
    assert world_state.get_timeline(world["id"])["Luca Bell"]
