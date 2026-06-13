import random

CHAOS_EVENTS = [
    "A food truck rolls in offering free pizza to everyone on the block.",
    "A mysterious glowing object lands in the park.",
    "The mayor announces all shops on this street must close by Friday.",
    "Someone on the block wins the lottery and starts spending lavishly.",
    "A local resident goes viral on social media for a ridiculous dance.",
    "The water supply is cut off for 24 hours — no one knows why.",
    "A celebrity is spotted moving into the apartment on 3rd floor.",
    "City Hall passes a new law: everyone must work from home starting tomorrow.",
    "A free outdoor concert is announced for tonight in the parking lot.",
    "A strange smell drifts from the abandoned building on the corner.",
    "Forecast says it will snow two inches in the next two hours — in June.",
    "A mysterious new neighbor arrives with no name tag and a locked suitcase.",
]


def random_event() -> str:
    return random.choice(CHAOS_EVENTS)
