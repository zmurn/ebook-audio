"""Slovenian stress from Sloleks, applied to Piper phonemes.

eSpeak guesses stress for words it does not know; Sloleks has the accented form
for ~1.5M word forms, which is the part of its data that was manually corrected.
We keep only the stress position:

    sl_stress.stress_of("cankar") -> 1      # CÁN-kar
    sl_stress.apply(phonemes, 1)             # move ˈ to the first vowel

The table is built by scripts/build_sloleks_stress.py into .cache/sloleks/.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache" / "sloleks" / "sloleks_stress.tsv.gz"
STRESS = ("ˈ", "ˌ")
VOWELS = set("aeiouɛɔəɐɑɒɨʉɯɪʊʏɜɞɘɵøœæɶʌ")

_MAP: dict[str, int] | None = None


def _load() -> dict[str, int]:
    global _MAP
    if _MAP is None:
        if not CACHE.exists():
            _MAP = {}
        else:
            table: dict[str, int] = {}
            with gzip.open(CACHE, "rt", encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 2:
                        continue
                    # several different accents for the same spelling = homograph
                    # (samo/samó/sámo); guessing one would make it worse
                    indices = parts[1].split(",")
                    if len(indices) == 1:
                        table[parts[0]] = int(indices[0])
            _MAP = table
    return _MAP


def available() -> bool:
    return CACHE.exists()


def stress_of(word: str) -> int | None:
    """1-based stressed syllable for a word form, or None."""
    cleaned = re.sub(r"[^\wČŠŽčšž'-]", "", word).lower()
    if not cleaned:
        return None
    table = _load()
    if cleaned in table:
        return table[cleaned]
    # try without a trailing clitic apostrophe / hyphen part
    base = cleaned.split("-")[0]
    return table.get(base)


def syllable_starts(phonemes: list[str]) -> list[int]:
    """Index of each vowel that begins a syllable."""
    starts: list[int] = []
    previous_vowel = False
    for i, p in enumerate(phonemes):
        is_vowel = p in VOWELS
        if is_vowel and not previous_vowel:
            starts.append(i)
        previous_vowel = is_vowel
    return starts


def apply(phonemes: list[str], index: int | None) -> list[str]:
    """Move the primary stress to the given syllable."""
    clean = [p for p in phonemes if p not in STRESS]
    if not index:
        return clean
    starts = syllable_starts(clean)
    if index < 1 or index > len(starts):
        return clean
    position = starts[index - 1]
    return clean[:position] + ["ˈ"] + clean[position:]


def coverage(words: list[str]) -> float:
    table = _load()
    if not words:
        return 0.0
    return sum(1 for w in words if w.lower() in table) / len(words)
