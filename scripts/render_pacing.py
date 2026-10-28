#!/usr/bin/env python3
"""Render passages with clause pacing (+ optional soft treatment).

H = Sloleks stress + clause pauses + varied speed, untreated.
I = the same, with a gentle EQ/compression/room pass.

Usage: .venv-piper/bin/python scripts/render_pacing.py            # H
       .venv-piper/bin/python scripts/render_pacing.py --soft     # I
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import stress_tts  # noqa: E402
from norm_sl import normalize  # noqa: E402
from pron_sl import pronounce  # noqa: E402
from pipeline import split_sentences  # noqa: E402

SOFT = (
    "highpass=f=75,"
    "equalizer=f=2600:t=q:w=1.6:g=-2.5,"
    "equalizer=f=7200:t=q:w=1.8:g=-2.0,"
    "lowpass=f=12000,"
    "acompressor=threshold=-20dB:ratio=1.8:attack=10:release=200,"
    "aecho=0.92:0.5:19|33:0.035|0.02"
)


def pause_for(sentence: str, paragraph_end: bool) -> float:
    if paragraph_end:
        return 0.85
    stripped = sentence.rstrip("«»\"' ")
    if stripped.endswith(("?", "!")):
        return 0.55
    return 0.45


def render(pid: str, text: str, soft: bool) -> Path:
    out_dir = ROOT / "bakeoff" / "out" / ("piper_pace_soft" if soft else "piper_pace")
    out_dir.mkdir(parents=True, exist_ok=True)
    rate = 22050
    pieces: list[np.ndarray] = []
    for block in text.split("\n\n"):
        sentences = split_sentences(block)
        for i, sentence in enumerate(sentences):
            wav = stress_tts.synthesize(sentence, speed=1.02)
            if wav is None:
                continue
            audio, sr = sf.read(wav, dtype="float32")
            rate = sr
            pieces.append(audio)
            pieces.append(np.zeros(int(sr * pause_for(sentence, i == len(sentences) - 1)), dtype=np.float32))
    audio = np.concatenate(pieces)
    audio = audio / max(1e-6, float(np.max(np.abs(audio)))) * 0.9
    tmp = out_dir / f"{pid}.raw.wav"
    sf.write(tmp, audio.astype(np.float32), rate)
    out = out_dir / f"{pid}.wav"
    chain = SOFT if soft else "anull"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", chain,
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    return out


def main() -> None:
    soft = "--soft" in sys.argv
    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}
    for pid in [a for a in sys.argv[1:] if not a.startswith("--")] or ["p1_narrative", "p2_dialogue", "p3_numbers"]:
        text, _ = normalize(passages[pid]["text"], minimal=True)
        text, _ = pronounce(text)
        out = render(pid, text, soft)
        print(f"{'I' if soft else 'H'} {pid} → {out} ({out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
