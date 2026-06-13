import os

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MOCK_SENTENCES = [
    "A street parade just showed up out of nowhere.",
    "Someone left a mysterious package on the sidewalk.",
    "The neighbors are arguing about something loud again.",
    "There's a strange light coming from the old building.",
    "I just saw something really weird down the block.",
]


def transcribe(audio_path: str | None) -> str:
    if not audio_path or MOCK:
        import random
        return random.choice(MOCK_SENTENCES)

    try:
        return _cohere_transcribe(audio_path)
    except Exception as e:
        print(f"[transcribe] failed: {e}")
        import random
        return random.choice(MOCK_SENTENCES)


def _cohere_transcribe(audio_path: str) -> str:
    api_key = os.environ.get("COHERE_API_KEY", "")
    if not api_key:
        print("[transcribe] no COHERE_API_KEY set, using fallback")
        import random
        return random.choice(MOCK_SENTENCES)

    import cohere

    co = cohere.ClientV2(api_key=api_key)

    with open(audio_path, "rb") as f:
        response = co.audio.transcriptions.create(
            model="cohere-transcribe-03-2026",
            language="en",
            file=f,
        )

    return response.text.strip() if response.text else ""


if __name__ == "__main__":
    print("Mock transcribe:", transcribe(None))
