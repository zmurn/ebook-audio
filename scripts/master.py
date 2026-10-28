#!/usr/bin/env python3
"""Loudness-normalise rendered segments to an audiobook target.

Two-pass ffmpeg loudnorm: -19 LUFS integrated, -3 dBTP true peak, 24 kHz mono.
This is the same step the real pipeline will run before packaging, and it makes
the bake-off fair — otherwise the hottest render wins on loudness alone.

Usage: python3 scripts/master.py [src_dir] [dst_dir]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bakeoff" / "out"
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "bakeoff" / "norm"

TARGET_I, TARGET_TP, TARGET_LRA = -19.0, -3.0, 11.0


def measure(path: Path) -> dict:
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    block = proc.stderr[proc.stderr.rfind("{"): proc.stderr.rfind("}") + 1]
    return json.loads(block)


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"no such directory: {SRC}")
    for voice_dir in sorted(SRC.iterdir()):
        if not voice_dir.is_dir():
            continue
        out_dir = DST / voice_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        for wav in sorted(voice_dir.glob("*.wav")):
            m = measure(wav)
            out = out_dir / wav.name
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(wav),
                    "-af",
                    (
                        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
                        f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
                        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
                        f":offset={m['target_offset']}:linear=true"
                    ),
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out),
                ],
                capture_output=True,
                check=True,
            )
            print(f"{wav.relative_to(SRC)} → {out.relative_to(ROOT)} "
                  f"(was {float(m['input_i']):.1f} LUFS)")


if __name__ == "__main__":
    main()
