#!/usr/bin/env python3
"""Render passages with the Maya1 Slovenian LoRA (3B speech-LM + SNAC).

The adapter expects espeak-ng `sl` IPA phonemes, not raw text — feeding
graphemes silently mispronounces. Runs on MPS when available, else CPU.

Usage: .venv-maya1/bin/python scripts/maya1_synth.py p1_narrative [--max-tokens 6000]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from peft import PeftModel
from phonemizer.backend import EspeakBackend
from phonemizer.separator import Separator
from snac import SNAC
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
PASSAGES = ROOT / "bakeoff" / "passages" / "passages.json"
OUT = ROOT / "bakeoff" / "out" / "maya1_lora"

CODE_END = 128258
OFFSET = 128266
SNAC_MIN, SNAC_MAX = 128266, 156937
DESC = "A Slovenian voice, speaker Artur-B-G0911."


def unpack_snac(ids: list[int]) -> list[torch.Tensor]:
    frames = len(ids) // 7
    ids = ids[: frames * 7]
    l1, l2, l3 = [], [], []
    for i in range(frames):
        s = ids[i * 7 : (i + 1) * 7]
        l1.append((s[0] - OFFSET) % 4096)
        l2 += [(s[1] - OFFSET) % 4096, (s[4] - OFFSET) % 4096]
        l3 += [(s[2] - OFFSET) % 4096, (s[3] - OFFSET) % 4096,
               (s[5] - OFFSET) % 4096, (s[6] - OFFSET) % 4096]
    return [l1, l2, l3]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("passage")
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--temperature", type=float, default=0.75)
    args = ap.parse_args()

    passages = {p["id"]: p for p in json.loads(PASSAGES.read_text())}
    text = passages[args.passage]["text"]

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    if lib := os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        pass
    be = EspeakBackend("sl", with_stress=True, preserve_punctuation=True)
    phonemes = be.phonemize([text], separator=Separator(phone="", word=" "), strip=True)[0]

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained("maya-research/maya1")
    model = AutoModelForCausalLM.from_pretrained(
        "maya-research/maya1", dtype=torch.bfloat16
    ).to(device)
    model = PeftModel.from_pretrained(model, "texdata/Maya1-Slovenian-TTS").eval()
    snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
    print(f"loaded in {time.time() - t0:.1f}s on {device}")

    prompt = tok.apply_chat_template(
        [{"role": "user", "content": f'<description="{DESC}"> {phonemes}'}],
        tokenize=False,
        add_generation_prompt=True,
    )
    ids = tok(prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

    t1 = time.time()
    with torch.inference_mode():
        out = model.generate(
            ids,
            max_new_tokens=args.max_tokens,
            do_sample=True,
            temperature=args.temperature,
            top_p=0.9,
            repetition_penalty=1.1,
            eos_token_id=CODE_END,
            pad_token_id=CODE_END,
        )
    gen = out[0, ids.shape[1] :].tolist()
    snac_ids = [t for t in gen if SNAC_MIN <= t <= SNAC_MAX]
    print(f"generated {len(gen)} tokens ({len(snac_ids)} audio) in {time.time() - t1:.1f}s")
    if len(snac_ids) % 7:
        print(f"warning: {len(snac_ids) % 7} trailing tokens dropped")

    codes = [torch.tensor(c, device=device).unsqueeze(0) for c in unpack_snac(snac_ids)]
    with torch.inference_mode():
        audio = snac.decoder(snac.quantizer.from_codes(codes))[0, 0].detach().cpu().numpy()

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.passage}.wav"
    sf.write(path, audio.astype(np.float32), 24000)
    print(f"wrote {path} ({len(audio) / 24000:.1f}s) total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
