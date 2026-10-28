#!/usr/bin/env python3
"""Sloleks 2.0 → compact stress table.

The IPA in Sloleks is auto-generated and its stress marks disagree with the
manually corrected accented spelling (Cánkar vs tsaŋˈkar). So we keep only what
is reliable: the syllable that carries the accent, derived from the accented
form. One line per word form:

    oblika<TAB>stress_syllable<TAB>naglašena_oblika<TAB>frequency

Usage: .venv-app/bin/python scripts/build_sloleks_stress.py
"""

from __future__ import annotations

import gzip
import re
import sys
import unicodedata
from pathlib import Path
from xml.etree.ElementTree import iterparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".cache" / "sloleks" / "Sloleks2.0.LMF" / "sloleks_clarin_2.0.xml"
OUT = ROOT / ".cache" / "sloleks" / "sloleks_stress.tsv.gz"

ACCENTS = {"\u0301", "\u0300", "\u0302", "\u0304"}  # acute, grave, circumflex, macron
VOWELS = set("aeiou")


def stress_index(accented: str) -> int | None:
    """1-based syllable carrying the accent, counting vowel nuclei."""
    decomposed = unicodedata.normalize("NFD", accented)
    accented_vowel_position = None
    syllables = 0
    previous_was_vowel = False
    for char in decomposed:
        if char in ACCENTS and previous_was_vowel:
            accented_vowel_position = syllables
            continue
        is_vowel = char in VOWELS
        if is_vowel and not previous_was_vowel:
            syllables += 1
        previous_was_vowel = is_vowel
    if accented_vowel_position is None:
        return None
    return accented_vowel_position or 1


def feats(element) -> dict[str, str]:
    return {f.get("att"): f.get("val") for f in element if f.tag.endswith("feat")}


def main() -> None:
    if not SRC.exists():
        sys.exit(f"missing {SRC}; download Sloleks 2.0 from hdl.handle.net/11356/1230")
    best: dict[str, dict] = {}
    seen = 0
    for _, element in iterparse(str(SRC), events=("end",)):
        if not (element.tag.endswith("FormRepresentation") or element.tag.endswith("Lemma")):
            continue
        data = feats(element)
        form = data.get("zapis_oblike")
        accented = data.get("naglašena_beseda_1")
        if not form or not accented:
            element.clear()
            continue
        idx = stress_index(accented)
        if idx is None:
            element.clear()
            continue
        frequency = int(data.get("pogostnost") or 0)
        key = form.lower()
        entry = best.setdefault(key, {"idx": set(), "freq": 0, "acc": accented})
        entry["idx"].add(idx)
        if frequency > entry["freq"]:
            entry["freq"] = frequency
            entry["acc"] = accented
        seen += 1
        if seen % 200_000 == 0:
            print(f"  {seen:,} forms, {len(best):,} unique", flush=True)
        element.clear()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        for form, entry in best.items():
            idx = ",".join(str(i) for i in sorted(entry["idx"]))
            f.write(f"{form}\t{idx}\t{entry['acc']}\t{entry['freq']}\n")
    print(f"{len(best):,} forms → {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
