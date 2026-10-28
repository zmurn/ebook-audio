#!/usr/bin/env python3
"""What does the eSpeak Slovenian front-end actually say?

Piper and the Maya1 LoRA both phonemise Slovenian through eSpeak-ng `sl`.
Before blaming the voice, check the front-end: if the phonemes are wrong, the
audio will be wrong no matter how good the acoustic model is.

Prints IPA next to the form a narrator would say, with a curated verdict.
The verdicts are analyst judgement (this is the normalizer's regression list),
the IPA is observed tool output.

Usage: python3 scripts/espeak_frontend_test.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

CASES = [
    # input, expected spoken form, verdict, note
    ("1848", "tisoč osemsto oseminštirideset", "ok", ""),
    ("1.278", "tisoč dvesto oseminsedemdeset", "ok", ""),
    ("36.500", "šestintrideset tisoč petsto", "ok", ""),
    ("2024", "dva tisoč štiriindvajset", "ok", ""),
    ("8:30", "osem trideset", "ok", ""),
    ("3 ure", "tri ure", "ok", ""),
    ("20 %", "dvajset odstotkov", "ok", ""),
    ("65 %", "petinšestdeset odstotkov", "ok", "blaga asimilacija v 'šezddeset'"),
    ("14,80 evra", "štirinajst evrov osemdeset centov", "napaka", "bere 'celih'"),
    ("3,5 kg", "tri kilograme in pol", "napaka", "bere 'celih' + črkovano enoto"),
    ("5 €", "pet evrov", "napaka", "valuta izgine"),
    ("2 kg", "dva kilograma", "napaka", "enota črkovana"),
    ("12 km/h", "dvanajst kilometrov na uro", "napaka", "črkovano + 'poševnica'"),
    ("21 °C", "enaindvajset stopinj Celzija", "napaka", "bere 'ce'"),
    ("3. nadstropju", "tretjem nadstropju", "napaka", "vrstilni kot glavni"),
    ("19. stoletju", "devetnajstem stoletju", "napaka", "vrstilni kot glavni"),
    ("5. poglavje", "peto poglavje", "napaka", "vrstilni kot glavni"),
    ("II. del", "drugi del", "napaka", "rimska kot glavni"),
    ("1. 5. 2024", "prvega maja dva tisoč štiriindvajset", "napaka", "datum razstavljen"),
    ("št. 12", "številka dvanajst", "napaka", "okrajšava nerazvozlana"),
    ("str. 5", "stran pet", "napaka", "okrajšava nerazvozlana"),
    ("dr. Novak", "doktor Novak", "napaka", "okrajšava nerazvozlana"),
    ("prof.", "profesor", "delno", "izgovori 'prof'"),
    ("npr.", "na primer", "napaka", "izgovori 'npr'"),
    ("itd.", "in tako dalje", "napaka", "izgovori 'itd'"),
    ("t. i.", "tako imenovani", "napaka", "črkovano"),
    ("A. Prešeren", "A Prešeren", "ok", "začetnica kot črka"),
]


def ipa(text: str) -> str:
    out = subprocess.run(
        ["espeak-ng", "-v", "sl", "-q", "--ipa", text],
        capture_output=True, text=True,
    )
    return " ".join(out.stdout.split())


def main() -> None:
    rows = []
    ok = partial = bad = 0
    for text, expected, verdict, note in CASES:
        if verdict == "ok":
            ok += 1
        elif verdict == "delno":
            partial += 1
        else:
            bad += 1
        rows.append((text, ipa(text), expected, verdict, note))

    lines = [
        "# eSpeak-ng `sl`: kaj front-end res izgovori",
        "",
        "Piper in Maya1 LoRA oba fonemizirata slovenščino skozi **eSpeak-ng `sl`**. "
        "Če je front-end napačen, je napačen tudi zvok — ne glede na to, kako dober je model.",
        "",
        f"**{ok} pravilnih, {partial} delnih, {bad} napačnih** od {len(CASES)} primerov. "
        "Nabor je namenoma sestavljen iz težkih primerov, ne iz povprečnega besedila.",
        "",
        "| Vhod | eSpeak IPA | Kar bi moral brati | Ocena | Opomba |",
        "|---|---|---|---|---|",
    ]
    for text, ipa_out, expected, verdict, note in rows:
        mark = {"ok": "✓", "delno": "~", "napaka": "✗"}[verdict]
        lines.append(f"| `{text}` | `{ipa_out}` | {expected} | {mark} | {note} |")

    lines += [
        "",
        "## Kaj to pomeni",
        "",
        "Glavne številke, letnice in ure eSpeak prebere prav. **Vrstilne številke, datumi, "
        "valuta, enote in okrajšave pa padejo** — natanko tisto, kar je v vsaki knjigi. "
        "Zato normalizacija ni 'dodatek za lepoto', ampak pogoj za uporaben posnetek.",
        "",
        "Ta tabela je hkrati regresijski seznam za `norm_sl`: vsak ✗ mora po normalizaciji "
        "postati ✓.",
    ]
    out = Path(__file__).resolve().parent.parent / "bakeoff" / "frontend.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
