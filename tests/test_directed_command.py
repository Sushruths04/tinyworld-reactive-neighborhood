import agents
import router
import world_state
from worlds import get_world


def test_directed_command_moves_only_addressee(monkeypatch):
    monkeypatch.setattr(agents, "MOCK", True)
    world = get_world("maple_street")
    world_state.reset_world(world["id"])
    world_state.init_cast(world)
    before = {c["name"]: world_state.get_position(world["id"], c["name"]) for c in world["cast"]}

    route = router.classify("Marta, go to the clinic", world)
    result = agents.react(world["id"], route["text"], route=route)

    assert [r["name"] for r in result["reactions"]] == ["Marta Voss"]
    after = {c["name"]: world_state.get_position(world["id"], c["name"]) for c in world["cast"]}
    assert after["Marta Voss"] == "nia_clinic"
    for name, pos in before.items():
        if name != "Marta Voss":
            assert after[name] == pos
