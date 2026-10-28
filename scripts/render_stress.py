#!/usr/bin/env python3
"""Render passages with Sloleks stress correction (100% local, no cloud).

eSpeak phonemises the whole sentence (so allophony and punctuation survive), we
split its phonemes at word boundaries, and move only the stress mark to the
syllable Sloleks marks. Unknown or ambiguous words keep eSpeak's stress.

Usage: .venv-piper/bin/python scripts/render_stress.py p1_narrative p3_numbers
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from piper import PiperVoice
from piper.config import SynthesisConfig

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sl_stress  # noqa: E402
from norm_sl import normalize  # noqa: E402
from pron_sl import pronounce  # noqa: E402
from pipeline import split_sentences  # noqa: E402

MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
OUT = ROOT / "bakeoff" / "out" / "piper_stress"
WORD = re.compile(r"[A-Za-zČŠŽčšž]+(?:['’-][A-Za-zČŠŽčšž]+)*")


def espeak_stress(phonemes: list[str]) -> int | None:
    seen = 0
    for p in phonemes:
        if p in sl_stress.STRESS:
            return seen + 1
        if p in sl_stress.VOWELS:
            seen += 1
    return None


def synthesize_sentence(voice: PiperVoice, text: str) -> tuple[np.ndarray, dict]:
    stats = {"words": 0, "known": 0, "moved": 0, "aligned": False}
    tokens = [t for t in re.split(r"\s+", text.strip()) if t]
    phonemes: list[str] = []
    for sentence in voice.phonemize(text):
        chunks = [c for c in "".join(sentence).split(" ") if c]
        if len(chunks) != len(tokens):
            phonemes.extend(sentence)  # cannot align: leave eSpeak alone
            continue
        stats["aligned"] = True
        for chunk, token in zip(chunks, tokens):
            piece = list(chunk)
            word = WORD.search(token)
            if word:
                stats["words"] += 1
                index = sl_stress.stress_of(word.group(0))
                if index:
                    stats["known"] += 1
                    if espeak_stress(piece) != index:
                        stats["moved"] += 1
                    piece = sl_stress.apply(piece, index)
            phonemes.extend(piece)
            phonemes.append(" ")
    ids = voice.phonemes_to_ids(phonemes)
    audio = voice.phoneme_ids_to_audio(ids, SynthesisConfig(length_scale=1.0))
    return audio, stats


def main() -> None:
    voice = PiperVoice.load(str(MODEL), config_path=str(MODEL) + ".json")
    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}
    OUT.mkdir(parents=True, exist_ok=True)
    for pid in sys.argv[1:] or ["p3_numbers"]:
        text, _ = normalize(passages[pid]["text"], minimal=True)
        text, _ = pronounce(text)
        chunks, total = [], {"words": 0, "known": 0, "moved": 0}
        for sentence in split_sentences(text):
            audio, stats = synthesize_sentence(voice, sentence)
            for k in total:
                total[k] += stats[k]
            chunks.append(audio)
            chunks.append(np.zeros(int(voice.config.sample_rate * 0.35), dtype=np.float32))
        audio = np.concatenate(chunks)
        audio = audio / max(1e-6, np.max(np.abs(audio))) * 0.9
        out = OUT / f"{pid}.wav"
        sf.write(out, audio.astype(np.float32), voice.config.sample_rate)
        print(f"{pid}: {len(audio)/voice.config.sample_rate:.1f}s, "
              f"{total['known']}/{total['words']} words known, "
              f"{total['moved']} stress corrections → {out}")


if __name__ == "__main__":
    main()
