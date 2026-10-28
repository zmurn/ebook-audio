#!/usr/bin/env python3
"""V4: vary the pacing, not the noise.

V2/V3 changed decoder noise and EQ; pitch movement stayed flat. This variant
changes *timing*: each sentence gets its own speed and its own pause, based on
what kind of sentence it is. Short dialogue snaps, long narration slows, a
paragraph break breathes longer than a full stop.

Usage: python3 scripts/prosody_v4.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from norm_sl import normalize  # noqa: E402
from pipeline import split_sentences  # noqa: E402

PIPER = ROOT / ".venv-piper" / "bin" / "piper"
MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
OUT = ROOT / "bakeoff" / "out" / "piper_v4"
WORK = ROOT / ".cache" / "v4"

CHAIN = (
    "highpass=f=70,"
    "equalizer=f=190:t=q:w=1.0:g=2.5,"
    "equalizer=f=3300:t=q:w=1.4:g=-2.5,"
    "equalizer=f=6800:t=q:w=2.0:g=-1.5,"
    "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=180:makeup=3,"
    "aecho=0.9:0.55:23|41|67:0.05|0.035|0.02"
)


def speed_for(sentence: str) -> float:
    """Long narration slows down, short dialogue snaps. Bounded to ±6 %."""
    n = len(sentence)
    if n > 170:
        return 1.07
    if n > 110:
        return 1.04
    if n < 55:
        return 0.98
    return 1.01


def pause_for(sentence: str, paragraph_end: bool) -> float:
    if paragraph_end:
        return 0.85
    stripped = sentence.rstrip("«»\"' ")
    if stripped.endswith(("?", "!")):
        return 0.55
    if stripped.endswith("…"):
        return 0.7
    return 0.45


def silence(seconds: float, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
             "-t", f"{seconds}", "-c:a", "pcm_s16le", str(path)],
            check=True, capture_output=True,
        )
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}

    for pid in ("p1_narrative", "p2_dialogue"):
        text, warnings = normalize(passages[pid]["text"])
        assert not warnings, warnings
        parts: list[Path] = []
        for block in text.split("\n\n"):
            sentences = split_sentences(block)
            for i, sentence in enumerate(sentences):
                wav = WORK / f"{abs(hash((sentence, speed_for(sentence)))) % 10**12}.wav"
                if not wav.exists():
                    subprocess.run(
                        [str(PIPER), "-m", str(MODEL), "-c", f"{MODEL}.json", "-f", str(wav),
                         "--length-scale", f"{speed_for(sentence):.3f}",
                         "--noise-scale", "0.70", "--noise-w-scale", "1.05",
                         "--sentence-silence", "0.2"],
                        input=sentence.encode(), check=True, capture_output=True,
                    )
                parts.append(wav)
                last = i == len(sentences) - 1
                parts.append(silence(pause_for(sentence, last), WORK / f"gap_{pause_for(sentence, last)}.wav"))

        listing = WORK / f"{pid}.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts))
        joined = WORK / f"{pid}_raw.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(listing), "-c", "copy", str(joined)], check=True, capture_output=True)
        staged = WORK / f"{pid}_stage.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-af", CHAIN,
                        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(staged)],
                       check=True, capture_output=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(staged), "-af",
             "loudnorm=I=-19:TP=-3:LRA=11", "-ar", "24000", "-ac", "1",
             "-c:a", "pcm_s16le", str(OUT / f"{pid}.wav")],
            check=True, capture_output=True,
        )
        print(f"v4/{pid} → {OUT / f'{pid}.wav'}")


if __name__ == "__main__":
    main()
