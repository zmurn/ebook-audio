#!/usr/bin/env python3
"""Objective prosody/timbre stats for rendered speech.

Robotic speech is measurable in two ways: pitch barely moves, and the spectrum
is bright and static. This prints both — F0 spread in semitones (the useful
unit for perceived monotony) and spectral centroid (brightness).

    .venv-maya1/bin/python scripts/f0_stats.py bakeoff/out/piper_v1 ...
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

FMIN, FMAX = 60.0, 350.0
WIN, HOP = 0.040, 0.010


def f0_track(x: np.ndarray, sr: int) -> tuple[np.ndarray, float]:
    w, h = int(WIN * sr), int(HOP * sr)
    lo, hi = int(sr / FMAX), int(sr / FMIN)
    out: list[float] = []
    centroids: list[float] = []
    for start in range(0, max(0, len(x) - w), h):
        frame = x[start:start + w].astype(np.float64)
        frame -= frame.mean()
        if np.sqrt((frame ** 2).mean()) < 1e-3:
            continue
        windowed = frame * np.hanning(w)

        spec = np.fft.rfft(windowed, 2 * w)
        ac = np.fft.irfft(spec * np.conj(spec), 2 * w)[:w]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lo:hi]
        if seg.size == 0:
            continue
        lag = lo + int(np.argmax(seg))
        if ac[lag] < 0.35:
            continue
        # guard against octave-up errors: if twice the lag correlates almost as
        # well, the true period is probably the longer one
        if 2 * lag < len(ac) - 1 and ac[2 * lag] > 0.8 * ac[lag] and 2 * lag < hi:
            lag = 2 * lag
        # parabolic interpolation around the peak
        if 0 < lag < len(ac) - 1:
            a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
            denom = a - 2 * b + c
            if abs(denom) > 1e-9:
                lag = lag + 0.5 * (a - c) / denom
        out.append(sr / lag)

        mag = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1 / sr)
        if mag.sum() > 0:
            centroids.append(float((freqs * mag).sum() / mag.sum()))

    return np.array(out), float(np.mean(centroids)) if centroids else 0.0


def describe(path: Path) -> dict:
    x, sr = sf.read(path, dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    f0, centroid = f0_track(x, sr)
    f0 = f0[np.isfinite(f0) & (f0 > 0)]
    duration = len(x) / sr
    if f0.size < 3:
        return {"file": str(path), "duration": duration, "voiced": 0.0}
    semis = 12 * np.log2(f0 / np.median(f0))
    return {
        "file": str(path),
        "duration": round(duration, 2),
        "voiced": round(f0.size * HOP / duration, 2),
        "median_f0": round(float(np.median(f0)), 1),
        "sd_semitones": round(float(semis.std()), 2),
        "range_semitones": round(float(np.percentile(semis, 90) - np.percentile(semis, 10)), 2),
        "centroid_khz": round(centroid / 1000, 2),
    }


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:]] or [Path("bakeoff/out/piper_v1")]
    rows = []
    for d in dirs:
        for wav in sorted(d.glob("*.wav")):
            if wav.stem.endswith((".raw", ".stage")):
                continue
            rows.append(describe(wav))

    print(f"{'file':34s} {'dur':>6s} {'voiced':>7s} {'F0':>6s} {'SD st':>6s} {'range st':>9s} {'centroid':>9s}")
    for r in rows:
        print(f"{r['file']:34s} {r.get('duration', 0):6.1f} {r.get('voiced', 0):7.2f} "
              f"{r.get('median_f0', 0):6.1f} {r.get('sd_semitones', 0):6.2f} "
              f"{r.get('range_semitones', 0):9.2f} {r.get('centroid_khz', 0):9.2f}")
    print("\nSD/range in semitones = how much the pitch moves. Higher = less monotone.")
    print("centroid = brightness. Lower = warmer, less 'glare'.")


if __name__ == "__main__":
    main()
