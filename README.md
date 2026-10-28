# ebook-audio — slovenske e-knjige v zvočne knjige

Osebno orodje: vzameš EPUB/PDF, ki ga imaš, in dobiš `.m4b` zvočno knjigo v slovenščini.
Lokalno, brez oblaka, brez računa, brez naročnine.

**Odločitve (sprejete 26. 10. 2026):**

1. **Osebna raba**, ne produkt za druge → ni potrebe po licenciranju, uporabnikih, obračunu.
2. **Samo lokalno** → glasovi tečejo na tem Macu (M1 Pro, 16 GB). Nobeno besedilo ne zapusti stroja.
3. **Najprej slepi test glasov** → preden zgradimo cevovod, ugotovimo, kateri glas je vreden desetih ur poslušanja.

## Namestitev na drug računalnik

Potrebuješ macOS (OCR skeniranih strani uporablja Apple Vision), `ffmpeg` in Python 3.10+.

```bash
brew install ffmpeg
git clone <repo> ebook-audio && cd ebook-audio
./setup.sh            # venvs + 63 MB glas + odvisnosti (~5 min)
.venv-app/bin/python app/server.py    # http://127.0.0.1:8765
```

Brez aplikacije, samo iz ukazne vrstice (uporabi `.venv-app`, ker ima vse odvisnosti):

```bash
.venv-app/bin/python pipeline.py knjiga.epub -o knjiga.m4b
```

Na Linuxu vse deluje razen OCR skeniranih strani (Apple Vision je macOS-only);
digitalni PDF-ji in EPUB-i delujejo normalno.

V repozitoriju **ni** modelov, predpomnilnikov, okolij ali tvojih knjig — vse to
ustvari `setup.sh` oziroma prvi zagon. Velikost klona je nekaj MB.

## Kje smo

| Faza | Stanje |
|---|---|
| 0. Slepi test glasov (Piper, Apple Tina, Maya1 LoRA) | **opravljen** — Maya1 izločen (0,12× realtime, degradira) |
| 1. EPUB → slovenski M4B, en glas | **dela na vzorcu** (pacing + studio chain) — [`examples/vzorec.m4b`](examples/vzorec.m4b) |
| 2. PDF pot (postavitev, OCR, reflow) | **dela** — digitalno + OCR, dvostranski skeni, obnova šumnikov |
| 3. Predvajalnik (poglavja, hitrost, spanje, nadaljevanje) | delno — spletni predvajalnik s poglavji |
| 4. Več jezikov, kloniranje glasu z dovoljenjem | ni začeto |

## Naglas iz Sloleks (neobvezno, brezplačno)

eSpeak ugiba naglas pri besedah, ki jih ne pozna. Sloleks 2.0 ima naglašene oblike
za ~888.000 besednih oblik; uporabimo jih kot tabelo naglasa.

```bash
./scripts/get_sloleks.sh        # 46 MB prenosa + 1,3 GB razpakiranja + 6 MB tabele
```

Nato v aplikaciji obkljukaj **Sloleks naglas**, ali:

```bash
.venv-app/bin/python pipeline.py knjiga.epub -o knjiga.m4b --stress
```

Podatki so licencirani **CC BY-NC-SA 4.0** (osebna raba); tabela se ne commita.
Pristop: eSpeak fonemizira celo poved (ohrani kontekst in ločila), mi premaknemo
samo oznako naglasa. Dvoumne oblike (`samo/samó/sámo`) se **preskočijo**, ne ugibajo.

## PDF in skenirane kopije

`pdf_ingest.py` odloči **na vsaki strani posebej**:

- **digitalna stran** (ima besedilni sloj) → PyMuPDF bloki, brez OCR
- **fotokopija** (brez besedila) → upodobitev pri 300 dpi + **Apple Vision OCR** (`sl-SI`, lokalno)

Ob tem rešuje tisto, kar v skeniranih knjigah res nastopa:

- **dvostranski posnetki** (odprta knjiga): stran s širino/višino > 1,15 se razdeli na polovici
- **tekoče glave/noge in številke strani**: vrstice, ki se ponavljajo na ≥ 30 % strani, se odstranijo
- **deljenje besed** čez vrstice (`beseda-` + nova vrstica) se združi
- **odstavki** iz OCR vrstic: po razmiku in po kratki vrstici, ki konča poved
- **naslovi poglavij**: večja višina vrstice + kratko besedilo; sicer TOC, sicer razdelitev po 12 strani
- **šumniki**: Vision pri majhni pisavi rad izgubi č/š/ž (`cez`), zato `ocr_fix.py` obnovi
  diakritiko iz slovenskih frekvenc (`wordfreq`): `cez → čez`

Rezultat se predpomni (`.cache/pdf/`), zato ponovno renderiranje ne OCR-a znova.

Omejitve: OCR še vedno dela napake (priporočljiv pregled besedila pred renderom);
enostranske dvostolpčne strani se ne delijo; rokopis in grafike se ne prepoznata;
hitrost ~1–2 s/stran.

## Aplikacija (lokalni spletni vmesnik)

```bash
.venv-app/bin/python app/server.py     # http://127.0.0.1:8765
```

Knjižnica, izbira nastavitev, čakalna vrsta z napredkom, predvajalnik s poglavji in
prenos M4B. Vse lokalno: strežnik posluša samo `127.0.0.1`, knjige in izdelki so v
`app/library/`, indeks v `app/library.db`.

Nastavitve v vmesniku ustrezajo glasovom iz slepega testa:

| Nastavitev | Učinek |
|---|---|
| Minimalni popravki | številke ostanejo številke (boljši naglas) — privzeto |
| Polni popravki | številke izpisane z besedo |
| Slovar imen | `Mozart → Mocart`, `Bach → Bah`, `Bregović → Bre-gović` |
| Tempo in pavze | počasnejši tempo, daljše pavze |
| Topel zvok in soba | EQ, kompresija, prostor |

## Cevovod (EPUB → M4B)

```bash
python3 scripts/make_sample_epub.py                       # testna knjiga
python3 pipeline.py examples/vzorec.epub -o examples/vzorec.m4b
```

Rezultat: M4B z oznakami poglavij, metapodatki, −19 LUFS, 64 kbps AAC.
Privzeto doda še tempo po tipu povedi in »studio« verigo (topel EQ, kompresija, mala
soba); `--plain` izklopi oboje za A/B.
Vsak stavek se predpomni po hashу (`.cache/tts`), zato popravek besedila
ponovno posname samo spremenjene stavke.

```bash
ffprobe -show_chapters examples/vzorec.m4b     # poglavja
```

Omejitve te faze: samo EPUB (PDF še ne), brez naslovnice, delitev stavkov je
heuristika, poglavja se preberejo na začetku (kot v resničnih knjigah).

## Slepi test

```bash
open bakeoff/index.html          # poslušaj in oceni
python3 scripts/measure.py       # meritve (trajanje, glasnost, tišina)
```

Stran je samostojna (brez strežnika, brez CDN). Imena glasov so skrita, dokler jih ne razkriješ;
ocene se shranijo v `localStorage`, izvoz v JSON. Glas C je isti kot B, le besedilo je šlo skozi
`norm_sl` — primerjaj p3 pri B in C.

```bash
/opt/homebrew/bin/python3.12 -m unittest discover -s tests -t .   # norm_sl testi
```

Rezultati in priporočilo: [`bakeoff/FINDINGS.md`](bakeoff/FINDINGS.md).
Raziskava o naravnosti in lokalnih modelih: [`RESEARCH-naturalness.md`](RESEARCH-naturalness.md).
Izgovorjava, fran.si, Sloleks in odločitev o glasu: [`PRONUNCIATION-DATA.md`](PRONUNCIATION-DATA.md).

Front-end (kaj eSpeak res izgovori): [`bakeoff/frontend.md`](bakeoff/frontend.md) — 9 ✓ / 17 ✗
od 27 težjih konstruktov. To je hkrati regresijski seznam za `norm_sl`.

## Zgradba

```
ebook-audio/
├── bakeoff/            # slepi test: odlomki, posnetki, stran, meritve
│   ├── passages/       # 3 testni odlomki (pripoved, dialog, številke)
│   ├── out/<glas>/     # renderirani wav
│   └── index.html      # generirano: scripts/build_page.py
├── examples/           # vzorčni EPUB + izdelan M4B
├── pdf_ingest.py       # PDF: digitalno besedilo ali OCR (Vision), struktura
├── ocr_fix.py          # obnova šumnikov po OCR
├── pipeline.py         # EPUB → poglavja → norm_sl → Piper → M4B
├── norm_sl/            # slovenska normalizacija: števniki, datumi, enote, okrajšave
├── pron_sl/            # izgovorni slovar tujih imen + audit neznanih imen
├── tests/              # unittest za norm_sl in pron_sl (20 testov)
├── scripts/
│   ├── measure.py      # LUFS, peak, tišina, hitrost govora
│   ├── master.py       # loudnorm na −19 LUFS / −3 dBTP
│   ├── build_page.py   # zgradi index.html iz podatkov
│   ├── espeak_frontend_test.py  # kaj eSpeak sl res izgovori
│   ├── humanize_v5.py  # dih, nagib tona, prostorski šum (poskus)
│   ├── asr_eval.py     # povratni ASR (Whisper) — le za pripoved
│   └── maya1_synth.py  # Maya1 LoRA (3B) → wav
└── .venv-*/            # ločena okolja: piper, maya1 (torch), asr (whisper)
```

## Načrt faze 1

Cevovod je namenoma razdeljen na korake, ki jih je mogoče testirati vsakega zase:

```
EPUB/PDF → ingest → clean → lang → norm_sl → synth → master → package
```

- **ingest** — EPUB prek `ebooklib` (spine = poglavja); PDF prek PyMuPDF samo kot rezerva.
- **clean** — odstrani tekoče glave/noge in številke strani, sestavi prelomljene vrstice, razreši deljenje.
- **lang** — `lingua` po odstavkih + prior cele knjige; sl/hr/sr je najbolj zamegljena skupina.
- **norm_sl** — številke z dvojino in sklonom, datumi v rodilniku, okrajšave, enote, rimske številke, `»…«`.
- **pron_sl** — tuja imena po slovensko (`Mozart → Mocart`, `Bach → Bah`), s sklanjatvijo
  (`Bacha → Baha`); neznana imena se samo predlagajo, ne prepišejo samodejno.
- **synth** — vmesnik `Engine.synthesize(text, voice, params) -> wav`; predpomnilnik po hashу.
  Prvi adapterji: Piper (CPU), Apple `say` (sistemski), Maya1 (MPS).
- **master** — `loudnorm` na ≈ −19 LUFS, true peak ≤ −3 dBTP, 0,7 s med poglavji.
- **package** — M4B z oznakami poglavij, naslovnico in metapodatki.

Znana omejitev: PDF, ki je skeniran, potrebuje OCR (`tesseract` s paketom `slv`) in ročni pregled
izluščenega besedila. Tega ne bomo pretvarjali, da je rešeno.

## Pravno

Pretvorba knjige, ki jo imaš, za lastno poslušanje je v zasebni sferi. Razširjanje ali prodaja
ustvarjenih posnetkov to ni — za to potrebuješ licenco. Brez obhodov DRM.

## Okolje

- macOS, Apple M1 Pro, 16 GB
- Python 3.12 (`/opt/homebrew/bin/python3.12`), ffmpeg 8.1, espeak-ng 1.52
- `.venv-piper` (piper-tts), `.venv-maya1` (torch 2.14 + MPS), `.venv-asr` (neuporabljen)
- Maya1 3B + LoRA + SNAC so prenešeni v `~/.cache/huggingface` (~6 GB)
