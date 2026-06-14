import json
import os
import sys
import time


MODAL_REACT_URL = os.environ.get("MODAL_REACT_URL", "")
MODAL_VOICE_URL = os.environ.get("MODAL_VOICE_URL", "")
MODAL_TRANSCRIBE_URL = os.environ.get("MODAL_TRANSCRIBE_URL", "")
PRIMARY_MODEL = "nvidia/Nemotron-Mini-4B-Instruct"


def _post_json(url, payload, timeout):
    import httpx

    started = time.time()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json(), round(time.time() - started, 2)


def check_llm():
    if os.environ.get("TINYWORLD_MOCK", "0") == "1":
        return True, "LLM: OFFLINE DEMO (TINYWORLD_MOCK=1)"
    if not MODAL_REACT_URL:
        return False, "LLM: UNREACHABLE (MODAL_REACT_URL is not set)"

    payload = {
        "event": "health check",
        "characters": [{
            "name": "Health Check",
            "job": "tester",
            "model": PRIMARY_MODEL,
        }],
        "prompts": {
            "Health Check": (
                "Reply with one short in-character sentence proving the model is awake. "
                "No labels, no JSON."
            )
        },
    }
    try:
        data, latency = _post_json(MODAL_REACT_URL, payload, timeout=180.0)
        reactions = data.get("reactions", [])
        text = (reactions[0].get("text") if reactions else "") or ""
        error = reactions[0].get("error") if reactions else True
        if error or not text.strip():
            return False, f"LLM: UNREACHABLE (empty/error response: {json.dumps(data)[:220]})"
        return True, f"LLM: LIVE ({PRIMARY_MODEL}, {latency:.2f}s)"
    except Exception as exc:
        return False, f"LLM: UNREACHABLE ({exc})"


def check_voice():
    if os.environ.get("TINYWORLD_SKIP_HEALTH_VOICE", "0") == "1":
        return True, "VOICE: SKIPPED"
    if not MODAL_VOICE_URL:
        return False, "VOICE: UNREACHABLE (MODAL_VOICE_URL is not set)"
    try:
        import httpx

        started = time.time()
        payload = {
            "text": "Health check.",
            "voice_desc": "(a clear calm voice)",
        }
        with httpx.Client(timeout=180.0, follow_redirects=True) as client:
            response = client.post(MODAL_VOICE_URL, json=payload)
            response.raise_for_status()
            size = len(response.content)
        if size < 100:
            return False, f"VOICE: UNREACHABLE (tiny response: {size} bytes)"
        return True, f"VOICE: LIVE ({round(time.time() - started, 2):.2f}s)"
    except Exception as exc:
        return False, f"VOICE: UNREACHABLE ({exc})"


def check_transcribe():
    if os.environ.get("TINYWORLD_SKIP_HEALTH_TRANSCRIBE", "0") == "1":
        return True, "TRANSCRIBE: SKIPPED"
    if not MODAL_TRANSCRIBE_URL:
        return False, "TRANSCRIBE: UNREACHABLE (MODAL_TRANSCRIBE_URL is not set)"
    try:
        import wave
        import math
        import struct
        import tempfile
        import httpx

        sample_rate = 16000
        duration = 0.25
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for i in range(int(sample_rate * duration)):
                    sample = int(2000 * math.sin(2 * math.pi * 440 * i / sample_rate))
                    wf.writeframes(struct.pack("<h", sample))
            with open(path, "rb") as f:
                audio = f.read()
            started = time.time()
            with httpx.Client(timeout=180.0, follow_redirects=True) as client:
                response = client.post(
                    MODAL_TRANSCRIBE_URL,
                    content=audio,
                    headers={"x-audio-suffix": ".wav"},
                )
                response.raise_for_status()
                response.json()
            return True, f"TRANSCRIBE: LIVE ({round(time.time() - started, 2):.2f}s)"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except Exception as exc:
        return False, f"TRANSCRIBE: UNREACHABLE ({exc})"


def main():
    checks = [check_llm(), check_voice(), check_transcribe()]
    for _, line in checks:
        print(line)
    return 0 if checks[0][0] else 1


if __name__ == "__main__":
    sys.exit(main())
