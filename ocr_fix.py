"""Repair OCR damage in Slovenian text.

Apple Vision is strong on scans but at body size it drops carons and š/ž
("čez" → "cez"), which changes the word. This restores diacritics using
Slovenian frequency data: strip the word, look it up, keep the most frequent
form that has diacritics. Only tokens without diacritics are touched.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache" / "sl_wordmap.json"
_DIA = "čšžČŠŽ"
_MIN_LEN = 3


def _strip(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _build() -> dict[str, str]:
    from wordfreq import top_n_list, zipf_frequency

    best: dict[str, tuple[str, float]] = {}
    for word in top_n_list("sl", 150_000):
        key = _strip(word)
        if key == word:
            continue
        score = zipf_frequency(word, "sl")
        if key not in best or score > best[key][1]:
            best[key] = (word, score)
    return {k: v[0] for k, v in best.items()}


def _load() -> dict[str, str]:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    mapping = _build()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(mapping, ensure_ascii=False))
    return mapping


_MAP: dict[str, str] | None = None


def restore(text: str) -> str:
    """Put diacritics back on words the OCR flattened."""
    global _MAP
    if _MAP is None:
        _MAP = _load()

    def fix(m: re.Match) -> str:
        token = m.group(0)
        if len(token) < _MIN_LEN or any(c in token for c in _DIA):
            return token
        candidate = _MAP.get(token.lower())
        if not candidate or candidate.lower() == token.lower():
            return token
        if token.isupper():
            return candidate.upper()
        if token[:1].isupper():
            return candidate[:1].upper() + candidate[1:]
        return candidate

    return re.sub(r"[A-Za-zČŠŽčšž]+", fix, text)
