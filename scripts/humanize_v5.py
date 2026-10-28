#!/usr/bin/env python3
"""V5: give the narration a body — breath, tone drift, room tone, human pauses.

Parameters come from measurements of audiobook reading, not taste:

  Bailly & Gouvernayre (2012), Interspeech — 4,000 pauses from real audiobooks:
    syntactic      366 ± 159 ms
    sentence-final 874 ± 293 ms
    paragraph     1426 ± 425 ms
    breath         355 ± 145 ms, in ~70 % of mid/long pauses
  Slovenian read speech: 4.5–6.5 syllables/s (normal), mean pause ~714 ms.

We take 0.9× of the measured pauses (the clips are short; full-size pauses can
drag) and add:
  - breath before ~70 % of paragraph pauses and ~15 % of sentence pauses
  - slow pitch drift: reset at paragraph, fall across it, dialogue a touch higher
  - continuous room tone so pauses are not digital silence

Usage: python3 scripts/humanize_v5.py [passage ...]
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from norm_sl import normalize  # noqa: E402
from pron_sl import pronounce  # noqa: E402
from pipeline import split_sentences  # noqa: E402

PIPER = ROOT / ".venv-piper" / "bin" / "piper"
MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
OUT = ROOT / "bakeoff" / "out" / "piper_v5"
WORK = ROOT / ".cache" / "v5"
SR = 22050

CHAIN = (
    "highpass=f=70,"
    "equalizer=f=190:t=q:w=1.0:g=2.5,"
    "equalizer=f=3300:t=q:w=1.4:g=-2.5,"
    "equalizer=f=6800:t=q:w=2.0:g=-1.5,"
    "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=180:makeup=3,"
    "aecho=0.9:0.55:23|41|67:0.05|0.035|0.02"
)

# measurement → our value (0.9× to keep the pace from dragging)
P_SENTENCE = 0.874 * 0.9
P_QUESTION = 0.95 * 0.9
P_PARAGRAPH = 1.426 * 0.9
BREATH_MEAN = 0.355
BREATH_AFTER = 0.25


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def wav_duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", str(path)]).stdout.decode().strip()
    return float(out)


def breath(seconds: float, seed: int) -> Path:
    """A soft inhale: band-limited noise with a slow attack and a longer tail."""
    path = WORK / f"breath_{seed}_{seconds:.2f}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        attack = seconds * 0.45
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
             "-i", f"anoisesrc=color=pink:sample_rate={SR}:amplitude=0.35:duration={seconds:.3f}",
             "-af", (f"highpass=f=320,lowpass=f=1500,"
                     f"afade=t=in:st=0:d={attack:.3f},"
                     f"afade=t=out:st={seconds - attack:.3f}:d={attack:.3f},"
                     f"volume=+2dB"),
             "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(path)])
    return path


def pitch_shift(src: Path, semitones: float, dst: Path) -> Path:
    """Shift pitch without changing duration (asetrate + atempo)."""
    ratio = 2 ** (semitones / 12)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-af", f"asetrate={int(SR * ratio)},aresample={SR},atempo={1 / ratio:.6f}",
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(dst)])
    return dst


def silence(seconds: float) -> Path:
    path = WORK / f"sil_{seconds:.3f}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
             "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{seconds:.3f}",
             "-c:a", "pcm_s16le", str(path)])
    return path


def say(text: str, speed: float, semitones: float) -> Path:
    key = hashlib.sha1(f"{MODEL.name}|{speed:.3f}|{semitones:.2f}|{text}".encode()).hexdigest()
    base = WORK / "tts" / f"{key}.wav"
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        raw = base.with_suffix(".raw.wav")
        run([str(PIPER), "-m", str(MODEL), "-c", f"{MODEL}.json", "-f", str(raw),
             "--length-scale", f"{speed:.3f}", "--noise-scale", "0.70",
             "--noise-w-scale", "1.05", "--sentence-silence", "0.2"],
            input=text.encode())
        if abs(semitones) < 0.01:
            raw.replace(base)
        else:
            pitch_shift(raw, semitones, base)
            raw.unlink(missing_ok=True)
    return base


def speed_for(sentence: str) -> float:
    n = len(sentence)
    return 1.07 if n > 170 else 1.04 if n > 110 else 0.98 if n < 55 else 1.01


def render(pid: str) -> Path:
    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}
    text, warnings = normalize(passages[pid]["text"])
    assert not warnings, warnings
    text, _ = pronounce(text)

    rng = random.Random(pid)
    parts: list[Path] = []
    drift = 0.0
    for block_index, block in enumerate(text.split("\n\n")):
        sentences = split_sentences(block)
        drift = 0.15 if block_index else 0.0  # slight reset at a new paragraph
        for i, sentence in enumerate(sentences):
            dialogue = sentence.lstrip().startswith("»")
            semis = drift + (0.2 if dialogue else 0.0)
            parts.append(say(sentence, speed_for(sentence), semis))
            drift = max(-0.6, drift - 0.08)  # declination across the paragraph

            last = i == len(sentences) - 1
            if last:
                pause, p_breath = P_PARAGRAPH, 0.7
            else:
                pause = P_QUESTION if sentence.rstrip("«» ").endswith(("?", "!")) else P_SENTENCE
                p_breath = 0.15

            if rng.random() < p_breath:
                seconds = max(0.22, min(0.5, rng.gauss(BREATH_MEAN, 0.05)))
                parts.append(silence(BREATH_AFTER))
                parts.append(breath(seconds, rng.randrange(10_000)))
                parts.append(silence(max(0.1, pause - BREATH_AFTER - seconds)))
            else:
                parts.append(silence(pause))

    listing = WORK / f"{pid}.txt"
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = WORK / f"{pid}_raw.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(joined)])

    # room tone: real pauses are never digital silence
    dur = wav_duration(joined)
    room = WORK / "room.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"anoisesrc=color=brown:sample_rate={SR}:amplitude=0.0016:duration={dur:.3f}",
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(room)])
    toned = WORK / f"{pid}_room.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-i", str(room),
         "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0",
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(toned)])

    OUT.mkdir(parents=True, exist_ok=True)
    staged = WORK / f"{pid}_stage.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(toned), "-af", CHAIN,
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(staged)])
    out = OUT / f"{pid}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(staged),
                    "-af", "loudnorm=I=-19:TP=-3:LRA=11", "-ar", "24000", "-ac", "1",
                    "-c:a", "pcm_s16le", str(out)], check=True, capture_output=True)
    return out


def main() -> None:
    pids = sys.argv[1:] or ["p1_narrative", "p2_dialogue"]
    for pid in pids:
        out = render(pid)
        print(f"{pid} → {out}  ({wav_duration(out):.1f}s)")


if __name__ == "__main__":
    main()
