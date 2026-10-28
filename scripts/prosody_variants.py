#!/usr/bin/env python3
"""Three ways to make the same Piper voice less robotic.

V1  current pipeline settings (baseline)
V2  more prosodic variation: higher noise_w, slightly slower
V3  V2 + a "studio" chain: EQ tilt, gentle compression, small room, room tone

Same text, same voice, same loudness target. Only the knobs change, so a
difference you hear is a difference we caused.

Usage: python3 scripts/prosody_variants.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from norm_sl import normalize  # noqa: E402

PIPER = ROOT / ".venv-piper" / "bin" / "piper"
MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
OUT = ROOT / "bakeoff" / "out"

# name → (piper flags, post chain or None)
VARIANTS = {
    "piper_v1": (["--length-scale", "1.0", "--noise-scale", "0.667", "--noise-w-scale", "0.8"], None),
    "piper_v2": (["--length-scale", "1.04", "--noise-scale", "0.70", "--noise-w-scale", "1.05"], None),
    "piper_v3": (
        ["--length-scale", "1.04", "--noise-scale", "0.70", "--noise-w-scale", "1.05"],
        # warm the low mids, tame the 3–7 kHz glare, glue it, put it in a small room
        "highpass=f=70,"
        "equalizer=f=190:t=q:w=1.0:g=2.5,"
        "equalizer=f=3300:t=q:w=1.4:g=-2.5,"
        "equalizer=f=6800:t=q:w=2.0:g=-1.5,"
        "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=180:makeup=3,"
        "aecho=0.9:0.55:23|41|67:0.05|0.035|0.02",
    ),
}

PASSAGES = {"p1_narrative", "p2_dialogue"}


def render(text: str, flags: list[str], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(PIPER), "-m", str(MODEL), "-c", f"{MODEL}.json", "-f", str(dest),
         "--sentence-silence", "0.35", *flags],
        input=text.encode(), check=True, capture_output=True,
    )


def post(src: Path, dst: Path, chain: str) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain,
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True, capture_output=True,
    )


def loudnorm(src: Path, dst: Path) -> None:
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
         "loudnorm=I=-19:TP=-3:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    m = json.loads(probe.stderr[probe.stderr.rfind("{"): probe.stderr.rfind("}") + 1])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
         f"loudnorm=I=-19:TP=-3:LRA=11:measured_I={m['input_i']}"
         f":measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
         f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True, capture_output=True,
    )


def main() -> None:
    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}
    for pid in sorted(PASSAGES):
        text, warnings = normalize(passages[pid]["text"])
        assert not warnings, warnings
        for name, (flags, chain) in VARIANTS.items():
            raw = OUT / name / f"{pid}.raw.wav"
            render(text, flags, raw)
            target = OUT / name / f"{pid}.wav"
            if chain:
                staged = OUT / name / f"{pid}.stage.wav"
                post(raw, staged, chain)
                loudnorm(staged, target)
            else:
                loudnorm(raw, target)
            print(f"{name}/{pid} → {target.name}")


if __name__ == "__main__":
    main()
