"""Piper synthesis with Sloleks-corrected stress (local, no cost).

The Piper CLI cannot take phonemes, so this uses the Python API: eSpeak
phonemises the sentence, we move the stress mark per Sloleks, and synthesise
from phoneme IDs. Falls back to the normal text path when alignment is unclear.

    from stress_tts import synthesize
    wav = synthesize("Jesensko jutro.", speed=1.0)
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import soundfile as sf

import sl_stress

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
CACHE = ROOT / ".cache" / "tts_stress"
WORD = re.compile(r"[A-Za-zČŠŽčšž]+(?:['’-][A-Za-zČŠŽčšž]+)*")

_voice = None


def _load():
    global _voice
    if _voice is None:
        from piper import PiperVoice
        _voice = PiperVoice.load(str(MODEL), config_path=str(MODEL) + ".json")
    return _voice


def _espeak_stress(phonemes: list[str]) -> int | None:
    seen = 0
    for p in phonemes:
        if p in sl_stress.STRESS:
            return seen + 1
        if p in sl_stress.VOWELS:
            seen += 1
    return None


def _sentence_phonemes(voice, text: str) -> tuple[list[str], dict]:
    stats = {"words": 0, "known": 0, "moved": 0}
    tokens = [t for t in re.split(r"\s+", text.strip()) if t]
    phonemes: list[str] = []
    for sentence in voice.phonemize(text):
        chunks = [c for c in "".join(sentence).split(" ") if c]
        if len(chunks) != len(tokens):
            phonemes.extend(sentence)
            continue
        for chunk, token in zip(chunks, tokens):
            piece = list(chunk)
            word = WORD.search(token)
            if word:
                stats["words"] += 1
                index = sl_stress.stress_of(word.group(0))
                if index:
                    stats["known"] += 1
                    if _espeak_stress(piece) != index:
                        stats["moved"] += 1
                    piece = sl_stress.apply(piece, index)
            phonemes.extend(piece)
            phonemes.append(" ")
    return phonemes, stats


def synthesize(text: str, speed: float = 1.0) -> Path | None:
    """Return a cached wav for one sentence, or None if it has no words."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text).strip()
    if not re.search(r"\w", text):
        return None
    key = hashlib.sha1(f"stress|{speed:.3f}|{text}".encode()).hexdigest()
    out = CACHE / key[:2] / f"{key}.wav"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    voice = _load()
    phonemes, _ = _sentence_phonemes(voice, text)
    ids = voice.phonemes_to_ids(phonemes)
    audio = voice.phoneme_ids_to_audio(
        ids, __import__("piper.config", fromlist=["SynthesisConfig"]).SynthesisConfig(length_scale=speed)
    )
    peak = float(np.max(np.abs(audio))) or 1.0
    sf.write(out, (audio / peak * 0.9).astype(np.float32), voice.config.sample_rate)
    return out


def stats_for(text: str) -> dict:
    phonemes, stats = _sentence_phonemes(_load(), text)
    return stats
