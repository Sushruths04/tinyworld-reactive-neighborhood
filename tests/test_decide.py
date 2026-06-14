import decide
from worlds import get_world


def test_malformed_json_degrades_to_safe_decision():
    decision = decide.parse_decision("not json", get_world("maple_street"), previous_mood="happy")
    assert decision.degraded is True
    assert decision.goto == "stay"
    assert decision.mood == "happy"


def test_guardrails_clamp_goto_mood_and_needs():
    raw = """
    {
      "think": "ok",
      "say": "I will check it now.",
      "action": "run somewhere impossible",
      "goto": "moon",
      "mood": "furious",
      "need_deltas": {"energy": -999, "hunger": 999, "social": 4}
    }
    """
    decision = decide.parse_decision(raw, get_world("maple_street"), previous_mood="curious")
    assert decision.goto == "stay"
    assert decision.mood == "curious"
    assert decision.need_deltas == {"energy": -25, "hunger": 25, "social": 4}


def test_dialogue_hygiene_removes_meta_line():
    raw = """
    {
      "think": "ok",
      "say": "As an AI, I should stay in character. I will help at the clinic.",
      "action": "help at the clinic",
      "goto": "nia_clinic",
      "mood": "proud",
      "need_deltas": {"energy": -5, "hunger": 0, "social": 3}
    }
    """
    decision = decide.parse_decision(raw, get_world("maple_street"), previous_mood="curious")
    assert "As an AI" not in decision.say
    assert decision.say == "I will help at the clinic."
    assert decision.goto == "nia_clinic"
