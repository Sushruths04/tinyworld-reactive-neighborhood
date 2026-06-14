#!/bin/bash
cd "$(dirname "$0")"
# Real inference on Modal (LLM + voice). Falls back to mock only if a call fails.
export TINYWORLD_MOCK=0
export MODAL_REACT_URL="https://mitvho09--tinyworld-inference-react-endpoint.modal.run"
export MODAL_VOICE_URL="https://mitvho09--tinyworld-inference-voice-endpoint.modal.run"
export MODAL_TRANSCRIBE_URL="https://mitvho09--tinyworld-inference-transcribe-endpoint.modal.run"
python3 health_check.py || true
python3 app.py
