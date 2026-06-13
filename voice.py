import os
import tempfile
import numpy as np

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MODAL_VOICE_URL = os.environ.get(
    "MODAL_VOICE_URL",
    "https://mitvho09--tinyworld-inference-voice-endpoint.modal.run",
)


def build_voice_description(character) -> str:
    return character.get("voice_description", "(a neutral voice)")


def generate_voice(text: str, voice_desc: str) -> str:
    try:
        if MOCK:
            return _mock_generate(text)
        else:
            return _real_generate(text, voice_desc)
    except Exception as e:
        print(f"[voice] generation failed: {e}")
        return _mock_generate(text)


def _mock_generate(text: str) -> str:
    sample_rate = 48000
    duration = 0.4
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.float32)
    path = os.path.join(tempfile.gettempdir(), f"tinyworld_voice_{os.getpid()}.wav")
    try:
        import soundfile as sf
        sf.write(path, audio, sample_rate)
    except ImportError:
        import wave
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    return path


def _real_generate(text: str, voice_desc: str) -> str:
    try:
        import httpx

        payload = {"text": text, "voice_desc": voice_desc}

        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            resp = client.post(MODAL_VOICE_URL, json=payload)
            resp.raise_for_status()

        path = os.path.join(tempfile.gettempdir(), f"tinyworld_voice_{os.getpid()}.wav")
        with open(path, "wb") as f:
            f.write(resp.content)

        return path

    except Exception as e:
        print(f"[voice] Modal call failed: {e}")
        return _mock_generate(text)


if __name__ == "__main__":
    import characters as c
    path = generate_voice("Hello there!", c.CHARACTERS[0]["voice_description"])
    print(path)
    assert os.path.exists(path), f"File not found: {path}"
    print("OK")
