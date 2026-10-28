"""Slovenian pronunciation layer: respell foreign names so the G2P says them right.

The front-end (eSpeak `sl`) has no idea that Mozart is [ˈmoːtsart] and Bach is
[ˈbax]. Slovenian solves this the way Slovenian always has: by adapting the
spelling. This module applies a curated lexicon and can suggest respellings for
names it has never seen.

    >>> pronounce("Mozart in Bach")
    ('Mocart in Bah', [('Mozart', 'Mocart'), ('Bach', 'Bah')])

Nothing is rewritten without either a lexicon entry or an explicit suggestion
call — same rule as norm_sl: do not guess silently.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["pronounce", "suggest", "audit", "LEXICON"]

LEXICON_PATH = Path(__file__).with_name("lexicon.tsv")


def _load() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in LEXICON_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            entries[parts[0].strip().lower()] = parts[1].strip()
    return entries


LEXICON = _load()
_BY_LENGTH = sorted(LEXICON, key=len, reverse=True)


def _match_case(replacement: str, original: str) -> str:
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# Slovenian case endings that can follow a foreign name. Only applied when the
# lexicon key ends in a consonant, so "Bach" matches "Bacha", "Bachu", "Bachom".
_CASE_ENDINGS = ("ega", "emu", "oma", "om", "em", "ih", "im", "ov", "ev", "a", "u", "e", "i", "o")


def _replace_once(text: str, pattern: str, target: str, changes: list[tuple[str, str]]) -> str:
    def replace(m: re.Match) -> str:
        replacement = _match_case(target, m.group("name")) + (m.groupdict().get("end") or "")
        changes.append((m.group(0), replacement))
        return replacement

    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def pronounce(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace known foreign names with their Slovenian respelling.

    Handles inflected forms (Bacha, Mozarta) by keeping the case ending.
    Returns the new text and the list of (original, replacement) pairs actually
    applied, so the pipeline can log exactly what it changed.
    """
    changes: list[tuple[str, str]] = []
    for source in _BY_LENGTH:
        target = LEXICON[source]
        escaped = re.escape(source).replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w)(?P<name>{escaped})(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            text = _replace_once(text, pattern, target, changes)
            continue
        if " " in source or source[-1] in "aeiou":
            continue
        # inflected form: Bach → Bacha, Mozart → Mozarta
        suffix = "|".join(_CASE_ENDINGS)
        pattern = rf"(?<!\w)(?P<name>{escaped})(?P<end>{suffix})(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            text = _replace_once(text, pattern, target, changes)
    return text, changes


# ------------------------------------------------------------------ suggestions
# Advisory only. The audit tool writes candidates for a human to approve.

_GERMAN = [
    (r"sch", "š"), (r"tz", "c"), (r"ß", "s"), (r"ch", "h"),
    (r"ei", "aj"), (r"eu", "oj"), (r"äu", "oj"),
    (r"ü", "i"), (r"ö", "e"), (r"ä", "e"),
    (r"^sp", "šp"), (r"^st", "št"), (r"v", "f"), (r"w", "v"), (r"z", "c"),
]
_ENGLISH = [
    (r"tion$", "šn"), (r"sh", "š"), (r"ch", "č"), (r"th", "t"),
    (r"ck", "k"), (r"oo", "u"), (r"ee", "i"), (r"ea", "i"),
    (r"wh", "v"), (r"w", "v"), (r"j", "dž"), (r"ay$", "ej"),
]
_FRENCH = [
    (r"eau", "o"), (r"ou", "u"), (r"qu", "k"), (r"gn", "nj"),
    (r"ch", "š"), (r"j", "ž"), (r"u", "i"),
    (r"(?<=[aeiou])s$", ""), (r"t$", ""), (r"e$", ""),
]
_ITALIAN = [
    (r"gli", "lji"), (r"gn", "nj"), (r"cc", "k"), (r"ch", "k"), (r"gh", "g"),
    (r"zz", "c"), (r"c(?=[ei])", "č"), (r"z", "c"),
]

_HINTS = [
    ("de", ("sch", "tz", "ß", "ü", "ö", "ä", "ei", "eu", "ch", "w")),
    ("en", ("tion", "sh", "th", "ck", "oo", "ee", "wh", "ay")),
    ("fr", ("eau", "ou", "qu", "gn", "ge", "oi")),
    ("it", ("gli", "gn", "cc", "zz", "chi", "che", "ghi")),
]
_RULES = {"de": _GERMAN, "en": _ENGLISH, "fr": _FRENCH, "it": _ITALIAN}


def _guess_language(token: str) -> str | None:
    low = token.lower()
    for lang, hints in _HINTS:
        if any(h in low for h in hints):
            return lang
    return None


def suggest(token: str) -> tuple[str, str, str] | None:
    """Propose a respelling for an unknown name: (respell, language, confidence)."""
    if token.lower() in LEXICON:
        return None
    lang = _guess_language(token)
    if not lang:
        return None
    out = token
    for pattern, replacement in _RULES[lang]:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    if out.lower() == token.lower():
        return None
    return out, lang, "low"


_FOREIGN_CHARS = set("qwxyäöüßèéêàçñșțøåæ")
_FOREIGN_DIGRAPHS = ("sch", "tz", "th", "sh", "ck", "wh", "eau", "gli", "cc")


def audit(text: str) -> list[tuple[str, str, str]]:
    """Find capitalised foreign-looking tokens with no lexicon entry.

    Returns (token, suggested respelling, language). Advisory: nothing is applied.
    """
    seen: dict[str, tuple[str, str, str]] = {}
    for token in re.findall(r"(?<!\w)[A-ZÄÖÜČŠŽ][\w'’-]{2,}(?!\w)", text):
        if token.lower() in LEXICON or token in seen:
            continue
        low = token.lower()
        if not (set(low) & _FOREIGN_CHARS or any(d in low for d in _FOREIGN_DIGRAPHS)):
            continue
        guess = suggest(token)
        if guess:
            seen[token] = (token, guess[0], guess[1])
    return list(seen.values())
