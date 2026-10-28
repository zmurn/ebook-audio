#!/usr/bin/env python3
"""Download the Maya1 stack and measure its speed on one short sentence.

Separated from maya1_synth.py so the slow download can run in the background
and the real render starts only once the weights are local.

Usage: .venv-maya1/bin/python -u scripts/maya1_probe.py
"""

from __future__ import annotations

import time

import torch
from huggingface_hub import snapshot_download

for repo in ("maya-research/maya1", "texdata/Maya1-Slovenian-TTS", "hubertsiuzdak/snac_24khz"):
    t0 = time.time()
    path = snapshot_download(repo)
    print(f"downloaded {repo} in {time.time() - t0:.0f}s → {path}", flush=True)

from peft import PeftModel
from phonemizer.backend import EspeakBackend
from phonemizer.separator import Separator
from snac import SNAC
from transformers import AutoModelForCausalLM, AutoTokenizer

device = "mps" if torch.backends.mps.is_available() else "cpu"
t0 = time.time()
tok = AutoTokenizer.from_pretrained("maya-research/maya1")
model = AutoModelForCausalLM.from_pretrained("maya-research/maya1", dtype=torch.bfloat16).to(device)
model = PeftModel.from_pretrained(model, "texdata/Maya1-Slovenian-TTS").eval()
snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
print(f"loaded in {time.time() - t0:.0f}s on {device}", flush=True)

text = "Danes je lep sončen dan in ptice pojejo na drevesih."
be = EspeakBackend("sl", with_stress=True, preserve_punctuation=True)
phonemes = be.phonemize([text], separator=Separator(phone="", word=" "), strip=True)[0]
prompt = tok.apply_chat_template(
    [{"role": "user", "content": f'<description="A Slovenian voice, speaker Artur-B-G0911."> {phonemes}'}],
    tokenize=False, add_generation_prompt=True,
)
ids = tok(prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

t0 = time.time()
with torch.inference_mode():
    out = model.generate(ids, max_new_tokens=800, do_sample=True, temperature=0.75,
                         top_p=0.9, repetition_penalty=1.1,
                         eos_token_id=128258, pad_token_id=128258)
elapsed = time.time() - t0
tokens = out.shape[1] - ids.shape[1]
audio_seconds = tokens / 7 / 24  # 24 frames per second of audio
print(f"generated {tokens} tokens in {elapsed:.0f}s "
      f"≈ {audio_seconds:.1f}s audio → {audio_seconds / elapsed:.3f}× realtime", flush=True)
print(f"10 h book would take ≈ {10 / max(audio_seconds / elapsed, 1e-6):.0f} h", flush=True)
