#!/usr/bin/env python3
"""Objective measurements for the Slovenian voice bake-off.

Measures duration, integrated loudness, true peak, silence share and speaking
rate for every rendered passage. These are sanity checks, not quality scores:
naturalness and stress only come from listening.

Usage: python3 scripts/measure.py
Writes bakeoff/metrics.json and bakeoff/results.md
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAKEOFF = ROOT / "bakeoff"
PASSAGES = BAKEOFF / "passages" / "passages.json"

# Display names; the bake-off page keeps them hidden until reveal.
VOICES = {
    "piper_min": {
        "name": "Piper · B + minimalni popravki",
        "engine": "VITS, minimalna normalizacija + imena",
        "params": "63 MB",
        "note": "Številke kot števke, popravljene le napake.",
    },
    "piper_pace": {
        "name": "Piper · Sloleks + pavze",
        "engine": "VITS + Sloleks + clause pauses",
        "params": "63 MB + 5,9 MB",
        "note": "Premori na vejicah, brez obdelave.",
    },
    "piper_pace_soft": {
        "name": "Piper · Sloleks + pavze + mehka obdelava",
        "engine": "VITS + Sloleks + pauses + soft EQ",
        "params": "63 MB + 5,9 MB",
        "note": "Nežen EQ, kompresija, mala soba.",
    },
    "piper_stress": {
        "name": "Piper · Sloleks naglas",
        "engine": "VITS + Sloleks naglas",
        "params": "63 MB + 5,9 MB tabele",
        "note": "Naglas iz slovarske baze, brez oblaka.",
    },
    "piper_min_nopron": {
        "name": "Piper · B + minimalni popravki brez imen",
        "engine": "VITS, minimalna normalizacija",
        "params": "63 MB",
        "note": "Brez izgovornega slovarja.",
    },
    "piper_textfix": {
        "name": "Piper · B + norm_sl + pron_sl",
        "engine": "VITS, brez obdelave",
        "params": "63 MB",
        "note": "Iste nastavitve kot B, le besedilo je popravljeno.",
    },
    "piper_artur": {
        "name": "Piper · sl_SI-artur-medium",
        "engine": "VITS (ONNX, CPU)",
        "params": "~63 MB",
        "note": "Edini vnaprej pripravljen slovenski glas, ki teče na CPU brez GPU.",
    },
    "piper_norm": {
        "name": "Piper · artur + norm_sl + pron_sl",
        "engine": "VITS + normalizacija + izgovorni slovar + tempo",
        "params": "63 MB",
        "note": "Isti glas kot piper_artur, le besedilo je normalizirano (samo p3).",
    },
    "apple_tina": {
        "name": "Apple · Tina (sl_SI)",
        "engine": "macOS sistemski glas",
        "params": "sistemski",
        "note": "Že nameščen na tem Macu; brezplačen, a ne prilagodljiv.",
    },
    "maya1_lora": {
        "name": "Maya1 · slovenski LoRA",
        "engine": "3B speech-LM + SNAC (GPU/CPU)",
        "params": "~6 GB",
        "note": "Isti govorec (ARTUR G0911) kot Piper, druga arhitektura.",
    },
}


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def duration(path: Path) -> float:
    out = run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path),
        ]
    )
    return float(out.strip())


def loudness(path: Path) -> tuple[float | None, float | None]:
    """Return (integrated LUFS, true peak dBFS) from ffmpeg's ebur128 filter."""
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-filter_complex", "ebur128=peak=true", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    text = proc.stderr
    lufs = peak = None
    summary = text.rsplit("Summary:", 1)[-1] if "Summary:" in text else text
    m = re.search(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", summary)
    if m:
        lufs = float(m.group(1))
    m = re.search(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", summary)
    if m:
        peak = float(m.group(1))
    return lufs, peak


def silence(path: Path) -> tuple[float, list[float]]:
    """Total silent time and long pauses (>=0.8 s) via silencedetect."""
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", "silencedetect=n=-40dB:d=0.4", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    total = 0.0
    for m in re.finditer(r"silence_duration:\s*(\d+(?:\.\d+)?)", proc.stderr):
        total += float(m.group(1))
    long_pauses = [float(x) for x in re.findall(r"silence_duration:\s*(0\.[89]\d*|[1-9]\d*(?:\.\d+)?)", proc.stderr)]
    return total, long_pauses


def main() -> None:
    passages = json.loads(PASSAGES.read_text())
    chars = {p["id"]: len(p["text"]) for p in passages}

    rows: list[dict] = []
    for voice_dir in sorted((BAKEOFF / "norm").iterdir()):
        if not voice_dir.is_dir():
            continue
        for wav in sorted(voice_dir.glob("*.wav")):
            pid = wav.stem
            if pid not in chars:
                continue
            dur = duration(wav)
            lufs, peak = loudness(wav)
            silent, long_pauses = silence(wav)
            rows.append(
                {
                    "voice": voice_dir.name,
                    "passage": pid,
                    "file": str(wav.relative_to(BAKEOFF)),
                    "duration_s": round(dur, 2),
                    "chars": chars[pid],
                    "chars_per_s": round(chars[pid] / dur, 1),
                    "lufs": lufs,
                    "true_peak_dbfs": peak,
                    "silence_share": round(silent / dur, 3) if dur else None,
                    "long_pauses": len(long_pauses),
                }
            )

    (BAKEOFF / "metrics.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")

    present = sorted({r["voice"] for r in rows})
    lines = ["# Rezultati meritve — slovenski bake-off", ""]
    lines.append(
        "Objektivne meritve so samo preverjanje razumljivosti in glasnosti. "
        "Naravnost in naglas se ne merita — to presodi uho."
    )
    lines.append("")
    lines.append("| Glas | Prehod | Trajanje | Znakov/s | LUFS | Peak dBFS | Tišina | Pavze >0,8 s |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['voice']} | {r['passage']} | {r['duration_s']} s | {r['chars_per_s']} | "
            f"{r['lufs']} | {r['true_peak_dbfs']} | {r['silence_share']:.1%} | {r['long_pauses']} |"
        )

    lines += ["", "## Glasovi", ""]
    for key in present:
        meta = VOICES.get(key, {"name": key, "engine": "?", "params": "?", "note": ""})
        lines.append(f"- **{meta['name']}** — {meta['engine']}, {meta['params']}. {meta['note']}")

    (BAKEOFF / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {BAKEOFF/'metrics.json'}")


if __name__ == "__main__":
    main()
