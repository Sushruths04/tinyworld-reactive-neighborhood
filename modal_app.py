import modal
import json

app = modal.App("tinyworld-inference")

llm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0",
        "transformers>=4.40",
        "accelerate",
        "sentencepiece",
        "protobuf",
        "fastapi[standard]",
    )
)

tts_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0",
        "voxcpm",
        "soundfile",
        "numpy",
        "fastapi[standard]",
    )
)


# ---------------------------------------------------------------------------
# LLM class — loads both models once, serves multiple characters
# ---------------------------------------------------------------------------

@app.cls(
    image=llm_image,
    gpu="A10G",
    timeout=900,
    scaledown_window=120,
)
class LLM:
    @modal.enter()
    def load_models(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self.models = {}
        self.tokenizers = {}

        model_ids = [
            "openbmb/MiniCPM5-1B",
        ]

        for mid in model_ids:
            print(f"Loading {mid}...")
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=True)
            mdl = AutoModelForCausalLM.from_pretrained(
                mid,
                torch_dtype="auto",
                device_map="auto",
                trust_remote_code=True,
            )
            self.tokenizers[mid] = tok
            self.models[mid] = mdl
            print(f"  {mid} loaded on {mdl.device}")

    @modal.method()
    def generate(self, model_id: str, prompt: str) -> str:
        import torch
        import re

        tok = self.tokenizers[model_id]
        mdl = self.models[model_id]

        messages = [{"role": "user", "content": prompt}]
        input_text = tok.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        inputs = tok(input_text, return_tensors="pt").to(mdl.device)

        with torch.no_grad():
            outputs = mdl.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.9,
                top_p=0.95,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        text = tok.decode(new_tokens, skip_special_tokens=True).strip()

        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if '<think>' in text:
            parts = text.split('</think>')
            if len(parts) > 1:
                text = parts[-1].strip()
            else:
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                text = paragraphs[-1] if paragraphs else ""
        if not text or len(text) < 10:
            text = "Hmm, that's interesting. Let me think about that."
        return text


# ---------------------------------------------------------------------------
# TTS class — VoxCPM2 voice synthesis
# ---------------------------------------------------------------------------

@app.cls(
    image=tts_image,
    gpu="A10G",
    timeout=300,
    scaledown_window=120,
)
class TTS:
    @modal.enter()
    def load_model(self):
        from voxcpm import VoxCPM

        print("Loading VoxCPM2...")
        self.model = VoxCPM.from_pretrained("openbmb/VoxCPM2")
        print("VoxCPM2 loaded.")

    @modal.method()
    def synthesize(self, text: str, voice_desc: str) -> bytes:
        import soundfile as sf
        import io
        import numpy as np

        full_text = f"{voice_desc}{text}"
        wav = self.model.generate(
            text=full_text,
            cfg_value=2.0,
            inference_timesteps=10,
        )

        buf = io.BytesIO()
        sf.write(buf, wav, self.model.tts_model.sample_rate, format="WAV")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Web endpoints — called by the Gradio app via HTTP
# ---------------------------------------------------------------------------

from fastapi import Request
from fastapi.responses import JSONResponse, Response


@app.function(image=llm_image, timeout=300)
@modal.fastapi_endpoint(method="POST")
async def react_endpoint(request: Request):
    """Accepts {event, characters, prompts}, returns list of reactions."""
    from fastapi import HTTPException

    body = await request.json()
    event = body.get("event", "")
    characters = body.get("characters", [])
    prompts = body.get("prompts", {})

    if not event or not characters:
        raise HTTPException(400, "event and characters required")

    llm = LLM()
    results = []

    for char in characters:
        name = char["name"]
        model_id = char["model"]
        prompt = prompts.get(name, "")

        if not prompt:
            results.append({
                "name": name,
                "job": char.get("job", ""),
                "model": model_id,
                "text": "[no prompt]",
                "error": True,
            })
            continue

        try:
            text = llm.generate.remote(model_id, prompt)
            results.append({
                "name": name,
                "job": char.get("job", ""),
                "model": model_id,
                "text": text,
                "error": False,
            })
        except Exception as e:
            results.append({
                "name": name,
                "job": char.get("job", ""),
                "model": model_id,
                "text": f"[error: {e}]",
                "error": True,
            })

    return JSONResponse(content={"reactions": results})


@app.function(image=tts_image, timeout=300)
@modal.fastapi_endpoint(method="POST")
async def voice_endpoint(request: Request):
    """Accepts {text, voice_desc}, returns WAV bytes."""
    from fastapi import HTTPException

    body = await request.json()
    text = body.get("text", "")
    voice_desc = body.get("voice_desc", "(a neutral voice)")

    if not text:
        raise HTTPException(400, "text required")

    tts = TTS()
    try:
        wav_bytes = tts.synthesize.remote(text, voice_desc)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {e}")
