#!/usr/bin/env python3
"""Render p3 with B's untouched settings and a chosen amount of text fixing.

  --mode full     numbers, dates, units, names   (the earlier D)
  --mode minimal  only what eSpeak gets wrong    (digits keep their stress)
  --no-pron       skip the name lexicon

Usage: python3 scripts/render_textfix.py --mode minimal -o bakeoff/norm/piper_min
"""

from __future__ import annotations

import argparse
import json
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
WORK = ROOT / ".cache" / "textfix"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "minimal"], default="minimal")
    ap.add_argument("--no-pron", action="store_true")
    ap.add_argument("-o", "--out", default="bakeoff/norm/piper_min")
    args = ap.parse_args()

    passages = {p["id"]: p for p in json.loads((ROOT / "bakeoff" / "passages" / "passages.json").read_text())}
    text, warnings = normalize(passages["p3_numbers"]["text"], minimal=args.mode == "minimal")
    assert not warnings, warnings
    if not args.no_pron:
        text, changes = pronounce(text)
        for src, dst in changes:
            print(f"  ~ {src} → {dst}")
    print("TEXT:", text)

    WORK.mkdir(parents=True, exist_ok=True)
    for old in WORK.glob("*.wav"):
        old.unlink()
    parts = []
    for i, sentence in enumerate(split_sentences(text)):
        wav = WORK / f"{i:03d}.wav"
        run([str(PIPER), "-m", str(MODEL), "-c", f"{MODEL}.json", "-f", str(wav),
             "--sentence-silence", "0.35"], input=sentence.encode())
        parts.append(wav)
    listing = WORK / "list.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = WORK / "joined.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(joined)])

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "p3_numbers.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(joined),
         "-af", "loudnorm=I=-19:TP=-3:LRA=11", "-ar", "24000", "-ac", "1",
         "-c:a", "pcm_s16le", str(out)])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
