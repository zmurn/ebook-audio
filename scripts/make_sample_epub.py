#!/usr/bin/env python3
"""Build a small Slovenian EPUB for end-to-end pipeline tests.

Stdlib only — no ebooklib, no network. Three chapters with the constructs that
break TTS: numbers, dates, units, abbreviations, dialogue quotes.

Usage: python3 scripts/make_sample_epub.py [out.epub]
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHAPTERS = [
    (
        "Jesensko jutro",
        """<p>Jesensko jutro se je vleklo čez Ljubljansko barje. Megla se je dvigala s travnikov
        in se ovijala okoli vrb, ki so stale ob jarku kakor utrujeni popotniki.</p>
        <p>Ana je stopila na prag, si ovila šal okoli vratu in prisluhnila. Nekje v daljavi je
        zaropotal vlak, za njim pa je nastala tista posebna tišina, ki jo poznajo samo ljudje,
        ki zgodaj vstajajo.</p>
        <p>»Še danes bo dež,« je rekla sama sebi in se nasmehnila.</p>""",
    ),
    (
        "Tretje nadstropje",
        """<p>V 3. nadstropju, v sobi št. 12, je dr. Novak odprl okno in pogledal proti Tromostovju.
        Ura je bila 8:30, temperatura 21 °C, vlaga 65 %, hitrost vetra pa 12 km/h.</p>
        <p>Na mizi je ležalo poročilo iz leta 1848, dolgo 36.500 besed. Prevoz z vlaka iz Maribora
        traja 2 uri in 15 minut, povratna vozovnica pa stane 14,80 evra.</p>
        <p>Novak je vzdihnil. »Tri ure,« je rekel. »Tri ure in še vedno nismo na začetku.«</p>""",
    ),
    (
        "Zadnji list",
        """<p>Ko je sonce zašlo, je Ana zaprla knjigo. Na zadnjem listu je bilo zapisano samo
        eno vprašanje, in to vprašanje je bilo dovolj.</p>
        <p>V 19. stoletju so v Križankah igrali Bacha, Mozarta in Beethovna. Danes tam nastopajo
        drugi ljudje, a tišina med kiticami je ostala ista.</p>
        <p>Knjiga ne bo ušla, si je rekla. Jutri bo spet jutro.</p>""",
    ),
]


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "examples" / "vzorec.epub"
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest, spine, files = [], [], {}
    for i, (title, body) in enumerate(CHAPTERS, 1):
        name = f"ch{i}.xhtml"
        files[f"OEBPS/{name}"] = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sl">
<head><title>{title}</title></head>
<body><h1>{title}</h1>
{body}
</body></html>"""
        manifest.append(f'<item id="ch{i}" href="{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="ch{i}"/>')

    files["OEBPS/content.opf"] = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:sl-sample-0001</dc:identifier>
    <dc:title>Vzorec za zvočno knjigo</dc:title>
    <dc:creator>Test</dc:creator>
    <dc:language>sl</dc:language>
  </metadata>
  <manifest>{''.join(manifest)}</manifest>
  <spine>{''.join(spine)}</spine>
</package>"""
    files["META-INF/container.xml"] = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""

    with zipfile.ZipFile(out, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    print(f"wrote {out} ({len(CHAPTERS)} chapters)")


if __name__ == "__main__":
    main()
