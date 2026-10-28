#!/usr/bin/env python3
"""Build a synthetic 'photocopy' PDF: page images, no text layer.

Used to test the scanned path: headers, page numbers, hyphenated line breaks,
and (with --spread) a two-page spread like a book photographed open.

Usage: python3 scripts/make_scan_pdf.py /tmp/scan.pdf [--spread]
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TEXT = """Jesensko jutro se je vleklo čez Ljubljansko barje. Megla se je dvigala s travnikov in se ovijala okoli vrb, ki so stale ob jarku kakor utrujeni popotniki. Ana je stopila na prag, si ovila šal okoli vratu in prisluhnila. Nekje v daljavi je zaropotal vlak, za njim pa je nastala tista posebna tišina, ki jo poznajo samo ljudje, ki zgodaj vstajajo.

V tretjem nadstropju, v sobi številka dvanajst, je doktor Novak odprl okno in pogledal proti Tromostovju. Ura je bila osem trideset, temperatura enaindvajset stopinj Celzija, vlaga petinšestdeset odstotkov, hitrost vetra pa dvanajst kilometrov na uro.

Na mizi je ležalo poročilo iz leta tisoč osemsto oseminštirideset, dolgo šestintrideset tisoč petsto besed. Prevoz z vlaka iz Maribora traja dve uri in petnajst minut, povratna vozovnica pa stane štirinajst evrov osemdeset centov."""

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def main():
    out = Path(sys.argv[1])
    spread = "--spread" in sys.argv
    body = ImageFont.truetype(FONT, 42)
    head = ImageFont.truetype(FONT, 64)
    small = ImageFont.truetype(FONT, 30)

    pages = []
    for chapter in ("Jesensko jutro", "Tretje nadstropje") * 3:
        img = Image.new("L", (1654, 2339), 248)  # A4 @ 200 dpi
        d = ImageDraw.Draw(img)
        d.text((140, 120), "Vzorec za zvočno knjigo", font=small, fill=120)
        y = 260
        d.text((140, y), chapter, font=head, fill=20); y += 130
        for block in TEXT.split("\n\n"):
            for line in wrap(d, block, body, 1350):
                d.text((140, y), line, font=body, fill=25); y += 62
            y += 28
        d.text((140, 2220), "— 7 —", font=small, fill=120)
        pages.append(img)

    if spread:
        out_pages = []
        for i in range(0, len(pages), 2):
            pair = pages[i:i + 2]
            width = sum(p.width for p in pair)
            canvas = Image.new("L", (width, pair[0].height), 255)
            x = 0
            for p in pair:
                canvas.paste(p, (x, 0)); x += p.width
            out_pages.append(canvas)
        pages = out_pages

    pages[0].save(out, "PDF", resolution=200.0, save_all=True, append_images=pages[1:])
    print(f"wrote {out} ({len(pages)} pages{' , spread' if spread else ''})")


if __name__ == "__main__":
    main()
