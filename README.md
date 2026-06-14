---
title: TinyWorld
emoji: 🏘️
colorFrom: cyan
colorTo: violet
sdk: gradio
sdk_version: "6.18.0"
app_file: app.py
pinned: false
tags:
  - hackathon
  - build-small
  - adventure-in-thousand-token-wood
  - openbmb/MiniCPM5-1B
  - nvidia/Nemotron-Mini-4B-Instruct
  - openbmb/VoxCPM2
  - cohere/cohere-transcribe-03-2026
---

# 🏘️ TinyWorld

**Throw an event. Watch the neighborhood react.**

A tiny pixel-art neighborhood where 5 AI characters react unpredictably, in their own voices, to whatever chaos you throw at them. Built for the **Build Small Hackathon 2026** (Hugging Face × Gradio), targeting the **Adventure in Thousand Token Wood** track.

## Source

Public GitHub repo: [Sushruths04/tinyworld-reactive-neighborhood](https://github.com/Sushruths04/tinyworld-reactive-neighborhood)

Built with OpenAI Codex. See the commit history for Codex-attributed commits.

## How to Play

1. **Type an event** in the textbox (or click 🎲 Random Chaos for inspiration).
2. **Hit ⚡ Trigger** — watch 5 speech bubbles spring up on the pixel map.
3. **Listen** — the most dramatic reaction auto-speaks via VoxCPM2 voice. Pick another character from the dropdown and hit 🔊 to hear them too.

## What Makes It Unpredictable

Every reaction is shaped by 4 hidden layers:
- **Mood** — each character has a secret mood that re-rolls after every event.
- **Memory** — they remember their last 3 reactions and reference them.
- **Relationships** — friendships, rivalries, and crushes color how they respond.
- **Surprise Seeds** — a random creative instruction appended to every prompt.

Trigger the same event 3 times → you get 3 completely different reactions each time.

## Models Used (all ≤ 4B params)

| Model | Params | Role | Sponsor |
|---|---|---|---|
| `nvidia/Nemotron-Mini-4B-Instruct` | 4B | Primary character dialogue model for all worlds | NVIDIA |
| `openbmb/MiniCPM5-1B` | 1B | Lightweight fallback dialogue model on Modal | OpenBMB |
| `openbmb/VoxCPM2` | 2B | Character voice synthesis (TTS) | OpenBMB |
| Whisper `base` on Modal | ~74M | Primary speech-to-text (mic input) | Modal |
| `Cohere Transcribe` | 2B | Speech-to-text fallback path | Cohere |

**Total model budget: under 10B params** (well under the 32B cap — earns the *Tiny Titan* badge).

## Built With

- [Gradio](https://gradio.app) — web UI framework
- [Hugging Face Spaces](https://huggingface.co/spaces) — deployment
- [ZeroGPU](https://huggingface.co/docs/transformers/optimization/bnbs#zero-gpu) — GPU access on Spaces

## Sponsor Credits

- **NVIDIA** — Nemotron-Mini-4B-Instruct (character dialogue)
- **OpenBMB** — MiniCPM5-1B fallback + VoxCPM2 voice synthesis
- **Modal** — serverless LLM, voice, and Whisper transcription endpoints
- **Cohere** — Transcribe fallback path

---

*Built for Build Small Hackathon 2026 · Hugging Face × Gradio · Thousand Token Wood track*
