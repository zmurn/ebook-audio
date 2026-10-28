"""Slovenian text normalisation for speech synthesis.

Takes book text and rewrites the parts a TTS front-end gets wrong: ordinals,
dates, money, units, abbreviations, Roman numerals, symbols. Returns the spoken
form plus warnings for anything it refused to guess at.

    >>> normalize("V 3. nadstropju, soba št. 12, dr. Novak.")
    ('V tretjem nadstropju, soba številka dvanajst, doktor Novak.', [])

Design rule: never silently guess. If a construct is ambiguous, leave it and
emit a warning so the pipeline can flag it for review.
"""

from __future__ import annotations

import re

__all__ = ["normalize", "int_to_words", "ordinal", "plural_form"]


# ---------------------------------------------------------------- numerals

_ONES = {
    0: "nič",
    1: ("en", "ena", "eno"),
    2: ("dva", "dve", "dve"),
    3: ("trije", "tri", "tri"),
    4: ("štirje", "štiri", "štiri"),
    5: "pet", 6: "šest", 7: "sedem", 8: "osem", 9: "devet",
    10: "deset", 11: "enajst", 12: "dvanajst", 13: "trinajst",
    14: "štirinajst", 15: "petnajst", 16: "šestnajst",
    17: "sedemnajst", 18: "osemnajst", 19: "devetnajst",
}
_TENS = {2: "dvajset", 3: "trideset", 4: "štirideset", 5: "petdeset",
         6: "šestdeset", 7: "sedemdeset", 8: "osemdeset", 9: "devetdeset"}
_HUNDREDS = {1: "sto", 2: "dvesto", 3: "tristo", 4: "štiristo",
             5: "petsto", 6: "šeststo", 7: "sedemsto", 8: "osemsto", 9: "devetsto"}
_GENDER_IX = {"m": 0, "f": 1, "n": 2, "count": 1}
# "count" is the form used before a counted noun: en kilogram, dva kilograma.

_COMPOUND_STEM = {1: "ena", 2: "dva", 3: "tri", 4: "štiri",
                  5: "pet", 6: "šest", 7: "sedem", 8: "osem", 9: "devet"}


_COUNT_FORMS = {1: "en", 2: "dva", 3: "tri", 4: "štiri"}


def _small(n: int, gender: str) -> str:
    if gender == "count" and n in _COUNT_FORMS:
        return _COUNT_FORMS[n]
    if n < 20:
        value = _ONES[n]
        return value[_GENDER_IX[gender]] if isinstance(value, tuple) else value
    if n < 100:
        unit, ten = n % 10, n // 10
        if unit == 0:
            return _TENS[ten]
        return f"{_COMPOUND_STEM[unit]}in{_TENS[ten]}"
    raise ValueError(f"not a small number: {n}")


def int_to_words(n: int, gender: str = "m") -> str:
    """Cardinal in Slovenian. Gender only affects 1-4 and counted nouns."""
    if n < 0:
        return "minus " + int_to_words(-n, gender)
    if n < 100:
        return _small(n, gender)

    parts: list[str] = []
    millions, rest = divmod(n, 1_000_000)
    if millions:
        if millions == 1:
            parts.append("milijon")
        else:
            parts.append(f"{int_to_words(millions)} "
                         f"{plural_form(millions, ('milijon', 'milijona', 'milijoni', 'milijonov'))}")
    thousands, rest = divmod(rest, 1000)
    if thousands:
        parts.append("tisoč" if thousands == 1 else f"{int_to_words(thousands)} tisoč")
    if rest >= 100:
        hundreds, rest = divmod(rest, 100)
        parts.append(_HUNDREDS[hundreds])
    if rest:
        parts.append(_small(rest, gender))
    return " ".join(parts)


def plural_form(n: int, forms: tuple[str, str, str, str]) -> str:
    """Singular / dual / plural / genitive-plural for a counted noun.

    1 → singular, 2 → dual, 3-4 → plural, everything else → genitive plural.
    11-14 are always genitive plural; 101-104 agree (their head is the unit),
    while 21 and 121 do not (their head is "dvajset").
    """
    last = abs(n) % 100
    if 11 <= last <= 14:
        return forms[3]
    return {1: forms[0], 2: forms[1], 3: forms[2], 4: forms[2]}.get(last, forms[3])


_ORD_STEM = {1: "prv", 2: "drug", 3: "tretj", 4: "četrt"}
_ORD_END = {"m": "i", "f": "a", "n": "o", "loc": "em", "locf": "i", "gen": "ega"}


def ordinal(n: int, gender: str = "m", case: str | None = None) -> str:
    """Ordinal in Slovenian: ordinal(3) → tretji, ordinal(3, case="loc") → tretjem."""
    if n <= 0:
        return str(n)
    end = _ORD_END[case or gender]
    if n < 5:
        return _ORD_STEM[n] + end
    if n == 100:
        return "stot" + end
    if n == 1000:
        return "tisoč" + end
    if n % 100 == 0 and n < 1000:
        return _HUNDREDS[n // 100] + "t" + end
    words = int_to_words(n).split()
    words[-1] += end
    return " ".join(words)


# ---------------------------------------------------------------- lexicon

MONTH_FORMS = {}  # filled below, maps nominative and genitive to the genitive

MONTHS_GEN = {
    "januar": "januarja", "februar": "februarja", "marec": "marca",
    "april": "aprila", "maj": "maja", "junij": "junija", "julij": "julija",
    "avgust": "avgusta", "september": "septembra", "oktober": "oktobra",
    "november": "novembra", "december": "decembra",
}
MONTH_FORMS = {**{k: v for k, v in MONTHS_GEN.items()}, **{v: v for v in MONTHS_GEN.values()}}

ABBREV = {
    "npr.": "na primer",
    "itd.": "in tako dalje",
    "itn.": "in tako naprej",
    "ipd.": "in podobno",
    "oz.": "oziroma",
    "tj.": "to je",
    "t. i.": "tako imenovani",
    "t.i.": "tako imenovani",
    "št.": "številka",
    "str.": "stran",
    "dr.": "doktor",
    "prof.": "profesor",
    "doc.": "docent",
    "mag.": "magister",
    "ing.": "inženir",
    "gos.": "gospodična",
    "sv.": "sveti",
    "prim.": "primerjaj",
    "gl.": "glej",
    "tzv.": "tako imenovani",
    "sl.": "slovensko",
    "angl.": "angleško",
    "nem.": "nemško",
    "lat.": "latinsko",
    "it.": "italijansko",
    "fr.": "francosko",
    "rus.": "rusko",
}

UNITS = {
    "km": ("kilometer", "kilometra", "kilometre", "kilometrov", "m"),
    "m": ("meter", "metra", "metre", "metrov", "m"),
    "cm": ("centimeter", "centimetra", "centimetre", "centimetrov", "m"),
    "mm": ("milimeter", "milimetra", "milimetre", "milimetrov", "m"),
    "kg": ("kilogram", "kilograma", "kilograme", "kilogramov", "m"),
    "g": ("gram", "grama", "grame", "gramov", "m"),
    "mg": ("miligram", "miligrama", "miligrame", "miligramov", "m"),
    "l": ("liter", "litra", "litre", "litrov", "m"),
    "dl": ("decilitr", "decilitra", "decilitre", "decilitrov", "m"),
    "ml": ("mililiter", "mililitra", "mililitre", "mililitrov", "m"),
    "h": ("ura", "uri", "ure", "ur", "f"),
    "min": ("minuta", "minuti", "minute", "minut", "f"),
    "s": ("sekunda", "sekundi", "sekunde", "sekund", "f"),
    "°c": ("stopinja", "stopinji", "stopinje", "stopinj", "f", "Celzija"),
    "%": ("odstotek", "odstotka", "odstotke", "odstotkov", "m"),
}

COMPOUND_UNITS = {
    "km/h": ("kilometer", "kilometra", "kilometre", "kilometrov", "m", "na uro"),
    "m/s": ("meter", "metra", "metre", "metrov", "m", "na sekundo"),
}

CURRENCIES = {
    "€": (("evro", "evra", "evre", "evrov"), ("cent", "centa", "cente", "centov")),
    "$": (("dolar", "dolarja", "dolarje", "dolarjev"), ("cent", "centa", "cente", "centov")),
}

# Words that are already inflected; the numeral only has to agree in gender.
WORD_UNITS = {
    "ura": "f", "uri": "f", "ure": "f", "ur": "f",
    "minuta": "f", "minuti": "f", "minute": "f", "minut": "f",
    "sekunda": "f", "sekundi": "f", "sekunde": "f", "sekund": "f",
    "stopinja": "f", "stopinji": "f", "stopinje": "f", "stopinj": "f",
    "leto": "n", "leti": "n", "leta": "n", "let": "n",
    "dan": "m", "dneva": "m", "dnevi": "m", "dni": "m",
    "evro": "m", "evra": "m", "evri": "m", "evrov": "m",
    "kilometer": "m", "kilometra": "m", "kilometri": "m", "kilometrov": "m",
    "kilogram": "m", "kilograma": "m", "kilogrami": "m", "kilogramov": "m",
    "odstotek": "m", "odstotka": "m", "odstotki": "m", "odstotkov": "m",
    "knjiga": "f", "knjigi": "f", "knjige": "f", "knjig": "f",
    "stran": "f", "strani": "f", "strani": "f",
    "beseda": "f", "besedi": "f", "besede": "f", "besed": "f",
    "oseba": "f", "osebi": "f", "osebe": "f", "oseb": "f",
    "hiša": "f", "hiši": "f", "hiše": "f", "hiš": "f",
    "soba": "f", "sobi": "f", "sobe": "f", "sob": "f",
    "stvar": "f", "stvari": "f", "misel": "f", "misli": "f",
}

ORDINAL_NOUNS = {
    "nadstropje": "n", "nadstropju": "nl", "nadstropja": "n",
    "stoletje": "n", "stoletju": "nl", "stoletja": "n",
    "tisočletje": "n", "tisočletju": "nl",
    "poglavje": "n", "poglavju": "nl", "poglavja": "n",
    "leto": "n", "letu": "nl", "leta": "n",
    "mesto": "n", "mestu": "nl", "mesta": "n",
    "obdobje": "n", "obdobju": "nl",
    "del": "m", "dela": "m", "delu": "ml",
    "oddelek": "m", "oddelku": "ml",
    "razred": "m", "razredu": "ml",
    "zvezek": "m", "zvezku": "ml",
    "letnik": "m", "letniku": "ml",
    "člen": "m", "členu": "ml",
    "izdaja": "f", "izdaji": "fl", "izdaje": "f",
    "knjiga": "f", "knjigi": "fl", "knjige": "f",
    "stran": "f", "strani": "fl",
    "soba": "f", "sobi": "fl",
    "etaža": "f", "etaži": "fl",
    "stopnja": "f", "stopnji": "fl",
    "sezona": "f", "sezoni": "fl",
    "faza": "f", "fazi": "fl",
    "epizoda": "f", "epizodi": "fl",
}

SYMBOLS = {"&": "in", "§": "paragraf", "№": "številka", "=": "enako", "×": "krat"}


# ---------------------------------------------------------------- helpers

def _num(groups: str) -> int:
    return int(re.sub(r"[.\s\u00a0]", "", groups))


def _capitalised(replacement: str, original: str) -> str:
    return replacement[0].upper() + replacement[1:] if original[:1].isupper() else replacement


def _unit_phrase(n: int, unit: tuple[str, ...]) -> str:
    forms, gender = unit[:4], unit[4]
    tail = unit[5] if len(unit) > 5 else None
    numeral_gender = "count" if gender == "m" else gender
    phrase = f"{int_to_words(n, numeral_gender)} {plural_form(n, forms)}"
    return phrase + (f" {tail}" if tail else "")


def _money(m: re.Match) -> str:
    whole, cents = _num(m.group(1)), int(m.group(2))
    major, minor = CURRENCIES.get(m.group(3).lower(), CURRENCIES["€"])
    if whole == 0:
        return _unit_phrase(cents, (*minor, "m"))
    head = _unit_phrase(whole, (*major, "m"))
    return head if cents == 0 else f"{head} {_unit_phrase(cents, (*minor, 'm'))}"


def _currency_only(m: re.Match) -> str:
    major, _ = CURRENCIES[m.group(2)]
    return _unit_phrase(int(m.group(1)), (*major, "m"))


def _date(m: re.Match) -> str:
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= day <= 31 or not 1 <= month <= 12:
        return m.group(0)
    month_name = list(MONTHS_GEN.values())[month - 1]
    return f"{ordinal(day, case='gen')} {month_name} {int_to_words(year)}"


def _date_named(m: re.Match) -> str:
    day, month, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    return f"{ordinal(day, case='gen')} {MONTH_FORMS[month]} {int_to_words(year)}"


def _ordinal_form(n: int, code: str) -> str:
    gender, locative = code[0], code.endswith("l")
    if not locative:
        return ordinal(n, gender)
    return ordinal(n, case="locf" if gender == "f" else "loc")


def _ordinal_noun(m: re.Match) -> str:
    number, noun = int(m.group(1)), m.group(2)
    return f"{_ordinal_form(number, ORDINAL_NOUNS[noun.lower()])} {noun}"


def _roman_noun(m: re.Match) -> str:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(m.group(1).upper()):
        value = values[ch]
        total += -value if value < prev else value
        prev = max(prev, value)
    noun = m.group(2)
    return f"{_ordinal_form(total, ORDINAL_NOUNS[noun.lower()])} {noun}" if total else m.group(0)


# ---------------------------------------------------------------- pipeline

_NOUN_RE = "|".join(sorted(ORDINAL_NOUNS, key=len, reverse=True))
_WORD_UNIT_RE = "|".join(sorted(WORD_UNITS, key=len, reverse=True))


def normalize(text: str, minimal: bool = False) -> tuple[str, list[str]]:
    """Rewrite Slovenian book text into what a narrator would actually say.

    minimal=True leaves plain integers, thousands, percentages and inflected
    unit words to eSpeak, which reads those with correct Slovenian stress.
    It rewrites only what the front-end actually gets wrong: money, dates,
    ordinals, symbols, abbreviations, and dual agreement for "2".

    Returns (spoken_text, warnings). Warnings name each construct that was
    ambiguous and deliberately left alone.
    """
    warnings: list[str] = []

    # 1. thousands separators: 1.278, 36.500 (digits are read with correct
    # stress, so minimal mode leaves them)
    if not minimal:
        text = re.sub(r"\b(\d{1,3}(?:\.\d{3})+)\b", lambda m: int_to_words(_num(m.group(1))), text)

    # 2. dates, before the ordinal rule can claim the day
    text = re.sub(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b", _date, text)
    text = re.sub(
        r"\b(\d{1,2})\.\s*(" + "|".join(MONTH_FORMS) + r")\s*(\d{4})\b",
        _date_named, text, flags=re.IGNORECASE,
    )

    # 2b. clock times: 8:30 → osem trideset
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b",
                  lambda m: f"{int_to_words(int(m.group(1)))} {int_to_words(int(m.group(2)))}", text)

    # 3. money with cents, then bare currency
    text = re.sub(
        r"\b(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})\s*(€|\$|evra|evrov|evro|eur|dolarja|dolarjev|usd)(?=\s|$|[.,;:!?])",
        _money, text, flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(\d+)\s*(€|\$)(?=\s|$|[.,;:!?])", _currency_only, text)

    # 4. number + compound unit (km/h, m/s)
    for pattern, unit in COMPOUND_UNITS.items():
        text = re.sub(rf"\b(\d+)\s*{re.escape(pattern)}(?=\s|$|[.,;:!?])",
                      lambda m, u=unit: _unit_phrase(int(m.group(1)), u),
                      text, flags=re.IGNORECASE)

    # 4b. decimal + unit: 3,5 kg → tri kilograme in pol
    def _decimal_unit(m: re.Match) -> str:
        whole, frac = int(m.group(1)), int(m.group(2))
        unit = UNITS[m.group(3).lower()]
        if frac == 5:
            return f"{_unit_phrase(whole, unit)} in pol"
        warnings.append(f"decimal unit without exact form: {m.group(0)!r}")
        return f"{_unit_phrase(whole, unit)} in {int_to_words(frac)} stotink"

    text = re.sub(
        r"\b(\d+),(\d+)\s*(°C|%|kg|mg|km|cm|mm|ml|dl|g|l|h|min|s)(?=\s|$|[.,;:!?])",
        _decimal_unit, text, flags=re.IGNORECASE,
    )

    # 8b. ambiguous dots: grams vs gospod, "sl." as slika before a number
    text = re.sub(r"\b(\d+)\s*g\.(?=\s+[a-zčšž])", lambda m: _unit_phrase(int(m.group(1)), UNITS["g"]), text)
    text = re.sub(r"\b(\d+)\s*g\.(?=\s+[A-ZČŠŽ])", lambda m: _unit_phrase(int(m.group(1)), UNITS["g"]) + ".", text)
    text = re.sub(r"(?<!\d)(?<!\d\s)\b([Gg])\.(?=\s+[A-ZČŠŽ])",
                  lambda m: "Gospod" if m.group(1) == "G" else "gospod", text)
    text = re.sub(r"\b([Gg])a\.(?=\s+[A-ZČŠŽ])",
                  lambda m: "Gospa" if m.group(1) == "G" else "gospa", text)
    text = re.sub(r"\bsl\.\s*(?=\d)", "slika ", text)

    # 5. number + symbol unit
    text = re.sub(
        (r"\b(\d+)\s*(°C|kg|mg|km|cm|mm|ml|dl|g|l|h|min|s)(?=\s|$|[.,;:!?])"
         if minimal else
         r"\b(\d+)\s*(°C|%|kg|mg|km|cm|mm|ml|dl|g|l|h|min|s)(?=\s|$|[.,;:!?])"),
        lambda m: _unit_phrase(int(m.group(1)), UNITS[m.group(2).lower()]),
        text, flags=re.IGNORECASE,
    )

    # 6. number + already-inflected unit word (2 uri, 15 minut). Minimal mode
    # only fixes dual agreement: eSpeak says "dva uri", it must be "dve uri".
    if minimal:
        text = re.sub(
            rf"\b2\s*({_WORD_UNIT_RE})\b",
            lambda m: ("dve " + m.group(1)) if WORD_UNITS[m.group(1).lower()] != "m" else m.group(0),
            text, flags=re.IGNORECASE,
        )
    else:
        text = re.sub(
            rf"\b(\d+)\s*({_WORD_UNIT_RE})\b",
            lambda m: f"{int_to_words(int(m.group(1)), WORD_UNITS[m.group(2).lower()])} {m.group(2)}",
            text, flags=re.IGNORECASE,
        )

    # 7. ordinals before a known noun
    text = re.sub(rf"\b(\d{{1,3}})\.\s*({_NOUN_RE})\b", _ordinal_noun, text, flags=re.IGNORECASE)

    # 8. Roman numerals, but only before a known noun — "M. Kacjan" is an initial
    text = re.sub(rf"\b([IVXLCDM]{{1,7}})\.\s*({_NOUN_RE})\b", _roman_noun, text)

    # 9. abbreviations, longest first so "t. i." wins over "t."
    for key in sorted(ABBREV, key=len, reverse=True):
        pattern = r"(?<![\w.])" + re.escape(key).replace("\\ ", r"\s+")
        text = re.sub(pattern, lambda m, r=ABBREV[key]: _capitalised(r, m.group(0)),
                      text, flags=re.IGNORECASE)

    # 10. symbols
    for symbol, spoken in SYMBOLS.items():
        text = text.replace(symbol, f" {spoken} ")

    # 11. remaining plain integers (minimal: eSpeak reads these correctly)
    if not minimal:
        text = re.sub(r"\b\d+\b(?!\.\s+[a-zčšž])", lambda m: int_to_words(int(m.group(0))), text)

    # 12. decimals without a known unit → generic fallback, flagged
    def _decimal(m: re.Match) -> str:
        warnings.append(f"decimal without known unit: {m.group(0)!r}")
        return f"{int_to_words(int(m.group(1)))} celih {int_to_words(int(m.group(2)))}"

    text = re.sub(r"\b(\d+),(\d+)\b", _decimal, text)

    # 13. leftover ordinals we could not resolve
    for m in re.finditer(r"(?<![\d.])\b(\d+|[IVXLCDM]{2,7})\.\s+(\w+)", text):
        warnings.append(f"ordinal before unknown noun: {m.group(0)!r}")

    # 14. punctuation and spacing
    text = (text.replace("–", ", ").replace("—", ", ")
                .replace("…", ".").replace("\u00a0", " "))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), warnings
