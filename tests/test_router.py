import router
from worlds import get_world


def test_directed_command_to_clinic():
    route = router.classify("Marta, go to the clinic", get_world("maple_street"))
    assert route["type"] == "directed_command"
    assert route["addressees"] == ["Marta Voss"]
    assert route["goto"] == "nia_clinic"


def test_world_event_and_ambient():
    world = get_world("maple_street")
    assert router.classify("the power goes out", world)["type"] == "world_event"
    assert router.classify("🙂", world)["type"] == "ambient"


def test_home_and_multi_addressee():
    world = get_world("maple_street")
    jay = router.classify("tell Jay to go home and rest", world)
    assert jay["addressees"] == ["Jay Park"]
    assert jay["goto"] == "jay_home"

    multi = router.classify("Marta and Jay, go to the cafe", world)
    assert multi["type"] == "directed_command"
    assert multi["addressees"] == ["Marta Voss", "Jay Park"]
    assert multi["goto"] == "cafe"


def test_riverside_clinic_alias():
    route = router.classify("Talia, go to the clinic", get_world("riverside_campus"))
    assert route["addressees"] == ["Talia Reed"]
    assert route["goto"] == "nurse_office"
