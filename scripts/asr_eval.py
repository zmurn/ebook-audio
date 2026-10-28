#!/usr/bin/env python3
"""Round-trip ASR check: is what we synthesized actually what the text says?

Whisper transcribes each rendered passage; the transcript is aligned against
the text the engine was asked to read. For p3 the reference is the *spoken*
form (numbers written out), otherwise every engine would look wrong.

This measures intelligibility and number/name reading, not beauty.

Usage: .venv-asr/bin/python scripts/asr_eval.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
import subprocess
import tempfile
from transformers import pipeline

ROOT = Path(__file__).resolve().parent.parent
BAKEOFF = ROOT / "bakeoff"
MODEL = "openai/whisper-small"


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = text.replace("«", " ").replace("»", " ").replace("„", " ").replace("“", " ")
    text = re.sub(r"[^\w\sščžćđ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def edit_distance(a: list[str], b: list[str]) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def rates(ref: str, hyp: str) -> tuple[float, float]:
    r, h = ref.split(), hyp.split()
    wer = edit_distance(r, h) / max(1, len(r))
    r2, h2 = list(ref.replace(" ", "")), list(hyp.replace(" ", ""))
    cer = edit_distance(r2, h2) / max(1, len(r2))
    return round(wer, 3), round(cer, 3)


def main() -> None:
    passages = {p["id"]: p for p in json.loads((BAKEOFF / "passages" / "passages.json").read_text())}
    rows, transcripts = [], {}
    asr = pipeline(
        "automatic-speech-recognition",
        model=MODEL,
        device="mps" if __import__("torch").backends.mps.is_available() else "cpu",
    )

    for voice_dir in sorted((BAKEOFF / "out").iterdir()):
        if not voice_dir.is_dir():
            continue
        for wav in sorted(voice_dir.glob("*.wav")):
            p = passages.get(wav.stem)
            if not p:
                continue
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-y", "-i", str(wav),
                     "-ac", "1", "-ar", "16000", tmp.name],
                    check=True,
                )
                audio, _ = sf.read(tmp.name, dtype="float32")
            result = asr(
                np.asarray(audio, dtype=np.float32),
                chunk_length_s=30,
                batch_size=1,
                generate_kwargs={"language": "sl", "task": "transcribe"},
            )
            hyp = normalise(result["text"])
            ref = normalise(p.get("spoken") or p["text"])
            wer, cer = rates(ref, hyp)
            rows.append(
                {
                    "voice": voice_dir.name,
                    "passage": wav.stem,
                    "wer": wer,
                    "cer": cer,
                    "words": len(ref.split()),
                }
            )
            transcripts[f"{voice_dir.name}/{wav.stem}"] = result["text"].strip()
            print(f"{voice_dir.name:14s} {wav.stem:13s} WER {wer:5.1%}  CER {cer:5.1%}")

    (BAKEOFF / "asr.json").write_text(
        json.dumps({"model": MODEL, "scores": rows, "transcripts": transcripts},
                   indent=2, ensure_ascii=False) + "\n"
    )

    lines = [
        "# Razumljivost (povratni ASR)",
        "",
        f"Whisper `{MODEL}`, jezik `sl`. Referenca za p3 je **izgovorjena oblika** "
        "(številke izpisane z besedo), sicer bi vsak sistem izgledal napačno.",
        "",
        "| Glas | Prehod | WER | CER |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['voice']} | {r['passage']} | {r['wer']:.1%} | {r['cer']:.1%} |")
    (BAKEOFF / "asr.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {(BAKEOFF/'asr.json')} and asr.md")


if __name__ == "__main__":
    main()
