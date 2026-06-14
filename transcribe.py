import os
from pathlib import Path

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MODAL_TRANSCRIBE_URL = os.environ.get(
    "MODAL_TRANSCRIBE_URL",
    "https://mitvho09--tinyworld-inference-transcribe-endpoint.modal.run",
)

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

    if MODAL_TRANSCRIBE_URL:
        try:
            text = _modal_transcribe(audio_path)
            if text:
                return text
        except Exception as e:
            print(f"[transcribe] Modal failed: {e}")

    try:
        return _cohere_transcribe(audio_path)
    except Exception as e:
        print(f"[transcribe] failed: {e}")
        import random
        return random.choice(MOCK_SENTENCES)


def _modal_transcribe(audio_path: str) -> str:
    import httpx

    path = Path(audio_path)
    headers = {"x-audio-suffix": path.suffix or ".wav"}
    with path.open("rb") as f:
        audio_bytes = f.read()

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.post(
            MODAL_TRANSCRIBE_URL,
            content=audio_bytes,
            headers=headers,
        )
        response.raise_for_status()

    data = response.json()
    return (data.get("text") or "").strip()


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
