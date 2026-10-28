# Izsledki — krog 1 (26. 10. 2026)

**Kratko:** preizkusila sta se dva lokalna glasova. Apple Tina je hitrejša in ima krajše trajanje
za isto besedilo; Piper je edini, ki ga lahko krmilimo — in zato edini, na katerem se splača
zgraditi cevovod. Noben ni na ravni knjižnega bralca. Največja ovira pa ni model, ampak
**front-end**: eSpeak napačno prebere 17 od 27 težjih konstruktov, ki jih najdeš v vsaki knjigi.

Kateri zveni bolje, ne trdim — tega ne morem slišati. Zato priporočilo spodaj temelji na
**nadzoru in meritvah**, ne na okusu. Končna sodba je tvoja, v `index.html`.

## Kaj je bilo preizkušeno

| Glas | Arhitektura | Velikost | Stanje |
|---|---|---|---|
| **Piper `sl_SI-artur-medium`** | VITS, ONNX, CPU | 63 MB | ✓ 3 odlomki |
| **Apple Tina (`sl_SI`)** | macOS sistemski glas | sistemski | ✓ 3 odlomki |
| **Maya1 + slovenski LoRA** | 3B speech-LM + SNAC | ~6 GB | ✗ prekinjeno: ~1,3 MB/s → 70+ min samo prenos |
| **Gepard + LoRA** | 555M, Qwen3.5 | ~1,1 GB | ✗ izločen: zahteva CUDA + vLLM |

Skripta za Maya1 je pripravljena (`scripts/maya1_synth.py`); manjka samo hitrejša povezava.

## Meritve

Vse je izenačeno na **−19 LUFS, −3 dBTP** (`scripts/master.py`), da glasnost ne vpliva na vtis.

| Glas | p1 pripoved | p2 dialog | p3 številke | Hitrost | 10 h knjiga |
|---|---|---|---|---|---|
| Piper artur | 27,1 s | 23,5 s | 46,0 s | 10,5× realtime | ≈ 1 h |
| Apple Tina | 24,7 s | 20,6 s | 41,8 s | 19,0× realtime | ≈ 30 min |

Pred izenačenjem je imel Piper **peak 0,1 dBFS** in −16 LUFS — torej že skoraj na meji
rezanja. Brez masteringa bi bila knjiga tišja od predogleda in hkrati bolj napeta.

## Razumljivost: kaj je ASR povedal in česa ni

Whisper-small je v pripovednem besedilu vrnil **CER 4,5–6,3 %** pri obeh glasovih — to je
spodnja meja, ker je model majhen. Pri p3 pa je odpovedal: številke prepisuje kot števke in
dela lastne napake (`1.278` → *»ena celih 277«*). Zato teh številk **ne objavljam kot oceno
izgovorjave** — pomerile bi Whisper, ne glasu. Za p3 velja le poslušanje.

## Ključna najdba: front-end, ne model

Piper in Maya1 oba fonemizirata slovenščino skozi **eSpeak-ng `sl`**. Če je tam napaka, je
napačen zvok ne glede na model. Preizkus: [`frontend.md`](frontend.md) — **9 ✓, 1 ~, 17 ✗**
od 27 namenoma težkih primerov.

Kaj gre prav: cela števila, letnice, ure, odstotki.
Kaj pade:

- vrstilne številke — `3. nadstropju` → *»tri nadstropju«*, `19. stoletju` → *»devetnajst stoletju«*
- datumi — `1. 5. 2024` → *»ena pet dva tisoč štiriindvajset«*
- denar in decimalke — `14,80 evra` → *»štirinajst celih osemdeset evra«*
- enote — `2 kg` → *»dva kəgə«*, `12 km/h` → *»dvanajst kəgə poševnica hə«*
- okrajšave — `št.` → *»šətə«*, `dr.` → *»dər«*, `npr.` → *»nəpər«*, `itd.` → *»itt«*
- rimske številke — `II. del` → *»dva del«*

To je tudi razlog, da je **normalizacija prvi del, ki ga je treba zgraditi** — ne okrasje na
koncu. Tabela v `frontend.md` je hkrati regresijski seznam: vsak ✗ mora po normalizaciji
postati ✓.

## Priporočilo

1. **Produkcija: Piper.** Edini, kjer lahko popravimo izgovorjavo (leksikon, fonemi),
   prozodijo po stavkih in hitrost. 63 MB, CPU, 10,5× realtime, brez omejitev ponovnega
   renderiranja. Cena: sintetičen, raven "medium".
2. **Predogled: Apple Tina.** 19× realtime, dovolj dober za vprašanje *»je besedilo pravilno
   izluščeno?«*, ne pa za končni posnetek — izgovorjave ne moremo popravljati.
3. **Maya1: pogojno.** Edini lokalni kandidat, ki bi lahko bil opazno bolj naraven. Cena je
   hitrost: 3B model na M1 pomeni ure do desetine ur na knjigo, plus 6 GB prenosa. Vredno
   poskusiti čez noč, ne v tem krogu.
4. **Gepard: ne.** CUDA + vLLM; na tem stroju ne teče.

## Kaj to pomeni za »zveni resnično«

Lokalno, na M1, s temi tremi možnostmi: **ne**. Realna meja je "zelo dobro branje stroja",
ne "bralec romana". Če je pogoj, da se po desetih urah ne naveličaš, je treba bodisi

- sprejeti to mejo in vložiti v normalizacijo, leksikon in prozodijo (največji donos na uro), bodisi
- ponovno odpreti odločitev o lokalnem-only in za končni render uporabiti komercialni glas.

Srednje poti ni: noben odprt model za slovenščino danes ni na ravni bralca.

## Naslednji korak

1. Poslušaj `index.html` (p1 in p3), oceni, izvozi povzetek.
2. Če se odločiš za Piper: zgradim `norm_sl` proti seznamu iz `frontend.md`, nato ingest → M4B.
3. Če hočeš Maya1: poženem čez noč in primerjamo isti tri odlomke.

---

# Krog 2 — tvoje ocene in popravek (26. 10. 2026)

## Ocene

| Glas | Izgovor | Naravnost | Vzdrži 10 ur | Za knjigo | Skupaj |
|---|---|---|---|---|---|
| **B — Piper** | 4 | 3 | **1** | 3 | **11** |
| **A — Apple Tina** | 4 | 1 | **1** | 1 | **7** |

Tvoja opomba: *»okrajšave kot km/h, dr. so izgovorjene kot črke namesto kar kratica
predlaga — ustvariti moramo sistem, kjer je slovenska logika za temi zadevami.«*

To je natanko tisto, kar je pokazal test front-enda. Pomembna posledica ocen: izgovorjava
je bila pri obeh že 4/5, **utrujenost pa 1/5 pri obeh**. To sta dve ločeni težavi —
normalizacija popravi prvo, ne druge.

## Kaj je zgrajeno

`norm_sl/` — slovenska logika pred sintezo:

- števniki z dvojino in množino (`1 evro`, `2 evra`, `5 evrov`; `2 uri`, `3 ure`, `5 ur`)
- vrstilne številke s sklonom (`tretjem nadstropju`, `devetnajstem stoletju`, `peto poglavje`)
- datumi v rodilniku (`prvega maja`), ure (`osem trideset`)
- denar (`štirinajst evrov osemdeset centov`), odstotki, enote (`dvanajst kilometrov na uro`)
- okrajšave (`št.`, `str.`, `dr.`, `npr.`, `itd.`, `t. i.`, `prof.`, …)
- rimske številke (`II. del` → `drugi del`) — samo pred znanim samostalnikom, da `M. Kacjan` ostane začetnica
- pravilo: **če ni znano, ne ugibaj** — vrne opozorilo za ročni pregled

Testi: `tests/test_norm_sl.py`, **11 testov, 0 napak** (`python3 -m unittest discover -s tests -t .`).

## Pred / po (isti glas, isti odlomek)

| Vhod | Prej (eSpeak) | Po `norm_sl` |
|---|---|---|
| `3. nadstropju` | `trˈiː natstrˈoːpju` | `tretjem nadstropju` → `trˈeːtjɛm natstrˈoːpju` |
| `št. 12` | `ʃˌətˈə dʋˈaːnajst` | `številka dvanajst` → `ʃtɛʋˈiːwka dʋˈaːnajst` |
| `dr. Novak` | `dˈər nˈoːʋak` | `doktor Novak` → `dˈɔːktɔr nˈoːʋak` |
| `12 km/h` | `dʋˈaːnajst kˌəmˈə pɔʃˈeːwnitsa xˈə` | `dvanajst kilometrov na uro` → `…kilɔmˈeːtrɔw nˈaː ˈuːrɔ` |
| `14,80 evra` | `ʃtˈiːrinajst tsˌelih ˈoːsəmdɛsɛt ˈeːʋra` | `štirinajst evrov osemdeset centov` |
| `21 °C` | `ˈɛːnaindʋˈaːjsɛt tsˈə` | `enaindvajset stopinj Celzija` |
| `1. 5. 2024` | `ˈɛːna pˈeːt dʋˈaː tˈiːsɔtʃ…` | `prvega maja dva tisoč štiriindvajset` |
| `II. del` | `dʋˈaː dˈeːw` | `drugi del` → `drˈuːɡi dˈeːw` |

V posnetku `piper_norm/p3_numbers.wav` (na strani **glas C**) ni več nobenega črkovanja:
trajanje pade s 46,0 s na 44,6 s, ker ni več `kəgə`, `pə`, `cə`.

## Česa `norm_sl` še ne pokrije

Znane omejitve, namenoma zapisane:

- **skloni pri števnikih** — trenutno nominativ/akuzativ; `z dvema knjigama`, `o treh` še ne
- **neznani samostalniki** za vrstilno številko → ostane številka + opozorilo (ne ugiba)
- **tuja imena** (`Bregović`, `Laibach`, `Chișinău`) — prepuščeno front-endu, brez leksikona
- **datumi brez letnice** (`3. maja`) in `od 5. do 8.` še niso pokriti
- **rimske številke** samo pred znanimi samostalniki

## Kaj to pomeni

Glas C dokazuje, da je **izgovor popravljiv z besedilom** — poceni, deterministično, brez
novega modela. Ne dokazuje pa, da je glas poslušljiv deset ur. Ocena **utrujenost 1/5 pri
obeh** ostaja odprta in je edina stvar, ki zdaj blokira projekt.

Zato je naslednji test Maya1 (3B): edini lokalni kandidat, ki lahko premakne *naravnost*,
ne le izgovora. Če tudi tam utrujenost ostane 1–2, je treba ponovno odpreti vprašanje
lokalnega-only — noben odprt slovenski model danes ni na ravni bralca.

---

# Krog 2b — Maya1 je bila izmerjena in izločena (26. 10. 2026)

Prenos je uspel (3B, 9,4 min; nalaganje 18 s na MPS). Rezultat je jasen:

| Lastnost | Meritev |
|---|---|
| Hitrost | **0,11–0,14× realtime** (4,9 s zvoka v 45 s; 24 s v 175 s) |
| 10 h knjiga | **70–90 h** računanja |
| Kratka poved (4,9 s) | pravilna: *»Jesensko jutro se je vleklo čez Ljubljansko barje.«* |
| Cel odlomek (24 s) | **degradira** — ponavlja in izpusti uvod |

Prepis celotnega odlomka (whisper-small, surov):

> Ha, ana je stopila naprak, si ovila šal okoli vratu in prisluhjela okoli vrp, ki so stale
> objala okoli vrp, ki so stale objarku kakoru trujeni popotniki. Ana je stopila naprak …
> Še danes bodeš je rekla sama sebi in se nasmehnila.

To ni napaka fonetike (to smo popravili) — to je degeneracija avtoregresivnega modela pri
daljšem generiranju. Zdravilo bi bilo rezanje na 1–2 povedi in ponovni poskusi, kar še
poveča ceno: 70–90 h na knjigo postane 100+ h, z negotovim izidom.

**Sklep: Maya1 ni pot za knjige na tem stroju.** Ostane referenca — na strani sta pod
»Maya1 (3B)« dva posnetka: kratka poved (uspe) in cel odlomek (degradira), da slišiš, kaj
3B prinese in kje odpove.

## Kam to pušča projekt

Lokalno, na M1 Pro, so vse tri možnosti zdaj izmerjene:

| Pot | Izgovor | Naravnost | Hitrost | Sodba |
|---|---|---|---|---|
| Apple Tina | 4/5 | 1/5 | 19× | predogled |
| Piper + `norm_sl` | **popravljen** | 3/5 | 10,5× | **edina pot za knjige** |
| Maya1 3B | dober (kratko) | neznan (dolgo odpove) | 0,12× | izločen |

Zato je naslednji korak **test na resničnem poglavju, ne na 30-sekundnih izrezih**:
utrujenost se pri kratkih posnetkih preceni. 10–15 minut neprekinjenega poslušanja pove,
ali je Piper + `norm_sl` dovolj za knjigo — in to je edino vprašanje, ki še ni odgovorjeno.

---

# Krog 3 — cevovod od EPUB do M4B (26. 10. 2026)

Prva različica `pipeline.py` + `norm_sl` je naredila celotno pot na vzorčni knjigi
(`examples/vzorec.epub`, 3 poglavja, 12 odstavkov):

| Preverjanje | Rezultat |
|---|---|
| Poglavja v M4B | 3, z meji 0–30,7 s / 30,7–73,9 s / 73,9–100,3 s |
| Metapodatki | naslov, album, `genre=Audiobook` |
| Glasnost | −19 LUFS, peak −2,8 dBFS |
| Trajanje | 1,7 min, 0,8 MB |
| Predpomnilnik | 24 stavkov (ponovni zagon ne sintetizira znova) |

Povratni prepis 2. poglavja potrdi, da so popravki slišni:

> Tretje nadstropje. **V tretjem nadstropju**, v sobi **številka 12**, je **doktor Novak**
> … temperatura **enaindvajset stopinj Celzija**, vlaga **petinšestdeset odstotkov**,
> hitrost vetra pa **dvanajst kilometrov na uro**.

(Podčrtano: oblike, ki jih surov eSpeak ni znal. Whisper številke prepisuje nazaj v
števke, zato jih navajam po besedah iz normaliziranega besedila.)

## Kaj je ta krog odkril

Cevovod je razkril napako, ki je test posameznih odlomkov ne bi: **naslov poglavja se je
prebral dvakrat**, ker je `<title>` iz `<head>` pricurljal v besedilo. Popravljeno
(`head`/`title` se preskočita); poglavje 2 se je skrajšalo z 43,1 s na 42,1 s. To je
argument za cevovod kot celoto — povezava med deli je, kjer se skrivajo napake.

## Česa še ni

- **PDF pot** (postavitev, OCR, reflow) — samo EPUB.
- **naslovnica** in poglavja z več glasovi.
- delitev stavkov je heuristika; kratice so sicer normalizirane, a `npr.` sredi stavka
  lahko še vedno razdeli stavek.
- **dolžina odstavka** vpliva na dihanje; zaenkrat je pavza med odstavki fiksna (0,35 s).

## Naslednje

1. Poslušaj `examples/vzorec.m4b` (1,7 min) — ali je ritem in pavze sprejemljiv.
2. Nato tvoja knjiga: `python3 pipeline.py tvoja.epub -o tvoja.m4b`.
   Pri 10,5× realtime je 10-urna knjiga ≈ 1 ura renderiranja.

---

# Krog 4 — zakaj zveni robotsko (26. 10. 2026)

Tvoja ocena: *»bolj robotsko je zvok kot izgovorjava«*. Tri različice istega glasu,
iste povedi, iste glasnosti — da vidimo, kateri vzvod sploh kaj premakne.

| Različica | Kaj spremeni | F0 SD | Razpon F0 | Središče spektra | Trajanje |
|---|---|---|---|---|---|
| **V1** | osnovno | 5,2 poltona | 12,0 | 1,15 kHz | 26,6 s |
| **V3** | toplejši EQ + blaga kompresija + mala soba | 5,7 | 14,1 | **1,08 kHz** | 28,6 s |
| **V4** | V3 + spremenljiv tempo in pavze | 5,4 | 13,9 | **1,07 kHz** | 29,9 s |

**Ključna ugotovitev: gibanja višine ni mogoče popraviti z nastavitvami.** Med 5,2 in
5,7 poltona pri vseh treh — to je lastnost modela, ne gumba. Tudi `noise_w` (V2, ki ga v
tabeli ni) je prinesel 6,0–6,1 poltona, torej nič.

Kar se je premaknilo in kar slišiš:

- **barva** — spekter se je ohladil s 1,15 na 1,07 kHz (manj "sija" pri 3–7 kHz, več
  toplote pri 190 Hz). To je čisto prava sprememba.
- **ritem** — V4 daje kratkim replikam hitrejši tempo (0,98×), dolgi pripovedi
  počasnejšega (1,07×), pavza po vprašanju je daljša od pavze po piki, odstavek diha 0,85 s.
- **prostor** — zelo blaga soba (trije zgodnji odboji, 5 % mokro) namesto anehoične tišine.

Vse troje je zdaj v `pipeline.py` (`STUDIO_CHAIN`, `speed_for`, `pause_for`); vzorec je
zato 1,9 min namesto 1,7, še vedno −19 LUFS in −3 dBTP. Primejraj na strani pod
»Zveni robotsko?«.

## Česa to ne popravi

Barva glasu ostaja barva 63 MB VITS modela z 22 kHz izhodom. Za drugačno barvo bi
potrebovali **drug model** — večji, bolje treniran slovenski TTS, ali konverzijo glasu
(voice conversion) na posnetek človeškega bralca. Z lokalnimi sredstvi na tem stroju
tega ni; to je meja, ne nastavitev.

Ocena **utrujenost** se zato ne bo popravila s parametri. Popravi se le z zamenjavo
modela — kar pomeni bodisi oblak bodisi čakanje na boljši odprt slovenski model.

---

# Krog 5 — slovenska izgovorjava tujih imen (26. 10. 2026)

Tvoja pripomba: *»Mozart, Bach in Laibach mu še delajo težave.«* Front-end tu nima
slovenske logike, ampak nemško-angleške heuristike, ki se uporabijo samo včasih:

| Ime | eSpeak reče | Slovenščina reče |
|---|---|---|
| Mozart | `mˈoːzart` | `mˈoːtsart` — *Mocart* |
| Bach | `bˈaːtsx` | `bˈaːx` — *Bah* |
| Beethoven | `bitxˈoːʋən` | `bˈeːtɔʋən` — *Betoven* |
| Laibach | `laˈiːbatsx` | `lˈaːjbax` — *Lajbah* |
| Shakespeare | `sxakɛspɛˈaːrɛ` | `ʃˈeːkspir` — *Šekspir* |
| Goethe | `ɡɔˈeːtxɛ` | `ɡˈeːtɛ` — *Gete* |
| Camus | `tsˈaːmus` | `kaˈmiː` — *Kami* |

## Kaj je zgrajeno

`pron_sl/` — izgovorni slovar, ki imena prepiše tako, kot jih slovenščina res
izgovori (to je isto, kar dela lektor):

- **49 vnosov** (`lexicon.tsv`), urejenih po izvoru: nemški (`sch → š`, `ei → aj`,
  `z → c`, `w → v`), angleški (`w → v`, `oo → u`), francoski (`eau → o`, `u → i`),
  italijanski (`c → č`, `ch → k`), ruski.
- **sklanjatev**: `Bacha → Baha`, `Mozarta → Mocarta`, `Beethovna → Betovna` —
  končnica se ohrani, jedro se popravi.
- **večbesedna imena**: `New York → Njujork`, `Sherlock Holmes → Šerlok Holms`.
- **`audit()`** — poišče neznana tuja imena v besedilu in predlaga prepis, a ga
  **ne uporabi sam**. Kandidati gredo v pregled; ista logika kot pri `norm_sl`:
  brez tihega ugibanja.
- **20 testov** skupaj (`norm_sl` + `pron_sl`), med njimi preverjanje končnih
  fonemov: `Bah → bˈaːx`, `Mocart → mˈoːtsart`, `Lajbah → lˈaːjbax`.

## Kar ostaja: naglas

eSpeak **ne sprejema oznak naglasa** (preizkušeno: `B'etoven` in `B'etoven` dasta
isto). Zato nekaj imen obdrži svoj privzeti (večinoma predzadnji) naglas:
`Betoven` → `bɛtˈoːʋən` (slovensko `BÉtoven`), `Kami` → `kˈaːmi` (slovensko `KamÍ`).

Obhod je tehnično dokazan, a še ni vgrajen: eSpeak sprejme foneme prek `[[...]]`,
Piperjev fonemizator pa jih **ne** (preizkušeno — vrne črke). Piper pa zna
sintetizirati neposredno iz fonemskih ID-jev, v mapi pa so tudi `ˈ` in `ˌ`. To je
naslednji korak, če bo naglas pri imenih še motil: obide se besedilo in se
sintetizira iz IPA z eksplicitnim naglasom.

## Učinek

Glas C na strani je zdaj **celotna produkcijska pot**: `norm_sl` (številke, datumi,
enote) + `pron_sl` (imena) + tempo po tipu povedi + mala soba. Trajanje p3 se je
zato podaljšalo s 44,9 na 49,8 s — počasnejši tempo in daljše pavze, ne napake.

---

# Krog 6 — dihanje, ton in prostor (26. 10. 2026)

V4 je najboljše, kar imamo. Zdaj ga poskušamo narediti bolj *človeškega* — ne z
drugim modelom, ampak s tem, kar človek počne med branjem: diha, spreminja ton in
nikoli ne bere v popolni tišini.

## Kaj pravijo meritve

Bailly in Gouvernayre (Interspeech 2012) sta analizirala **4.000 premorov** iz
resničnih zvočnih knjig, posnetih z bližnjim mikrofonom:

| Premor | Dolžina |
|---|---|
| znotraj povedi (sintaktični) | 366 ± 159 ms |
| ob koncu povedi | 874 ± 293 ms |
| ob koncu odstavka | **1426 ± 425 ms** |
| dih | **355 ± 145 ms**, v ~70 % daljših premorov |

Za slovenščino: normalna hitrost branega govora **4,5–6,5 zlogov/s**, povprečen
premor v govoru ~714 ms (diplomsko delo, UL).

## Kaj V5 doda

| Element | Parameter | Zakaj |
|---|---|---|
| pavza med povedmi | 0,79 s (0,9 × 874 ms) | izmerjeno, ne ugibano |
| pavza med odstavki | 1,28 s (0,9 × 1426 ms) | mejnik strukture |
| dih | 355 ms ± 50, pred 70 % odstavčnih in 15 % stavčnih pavz | človek ne bere brez zraka |
| ton | počasen nagib: reset +0,15 poltona na odstavku, −0,08 na poved; dialog +0,2 | deklaracija in menjava registra |
| prostor | stalni rjavi šum −56 dBFS | pravi posnetki nimajo digitalne tišine |

0,9× izmerjenih pavz je kompromis: pri kratkih odlomkih bi polne pavze vlekle.

## Meritve V4 → V5

| | F0 SD | Razpon | Središče spektra | Trajanje p1 | Trajanje p2 |
|---|---|---|---|---|---|
| V4 | 5,38 | 13,90 | 1,07 kHz | 29,9 s | 25,2 s |
| **V5** | **5,62** | **14,26** | **1,05 kHz** | 32,0 s | 28,0 s |

Gibanje tona se je povečalo za ~4 %, spekter se je ohladil, knjiga je 7–11 % daljša.
Dih je 15 dB pod govorom (merjeno), torej slišen v pavzi, ne čez besedo.
To niso velike številke — in to je pošteno: **barva glasu ostaja ista**.

## Tveganje

Sintetiziran dih je najbolj tvegan del: če zveni kot šum, bo slabše od tišine.
Zato je dih ločen od ostalega — v `humanize_v5.py` ga izklopiš z `p_breath = 0`,
ton in soba pa ostaneta. Poslušaj V5 na strani; če dih moti, obdržimo nagib in
prostor, dih pa ven.

---

# Krog 7 — B je bil najbolj naraven, ker ni bil obdelan (26. 10. 2026)

Tvoja sodba: *»Glas B je najbolj naraven, a ne vsebuje številk, imen, tempa in male sobe.«*

To je najpomembnejša povratna informacija doslej, ker loči dve stvari, ki smo ju mešali:

- **B** = neobdelan Piper (surovo besedilo, brez EQ, sobe, tempa) → najbolj naraven.
- **C** = B + popravki + tempo + soba → pravilen, a manj naraven.

Torej obdelava ni izboljšala naravnosti; **kupila je pravilnost za ceno naravnosti**.

## D — B + popravki, brez obdelave

Dodan je glas **D**: `norm_sl` + `pron_sl` na B-jevih nastavitvah, brez EQ, sobe,
tempa in nagiba. Dolžina 43,0 s (B 46,0 s, C 49,8 s). Če D zveni kot B, a z
`Mocarta`, `Baha`, `Betovna`, `štirinajst evrov` — je to naš novi privzetek.

Raziskava o tem, kako naravnost rešujejo drugi sistemi in kaj je realno lokalno:
[`../RESEARCH-naturalness.md`](../RESEARCH-naturalness.md).

---

# Krog 8 — zakaj je imel B boljšo izgovorjavo od D (26. 10. 2026)

Tvoja ugotovitev: *»D je najboljši, a B ima boljšo izgovorjavo večine stvari.«*
To se je izkazalo za natančno diagnozo, ne le vtis.

## Vzrok: eSpeak bere števke bolje kot izpisane števnike

Primerjava fonemov istega besedila:

| Vhod | eSpeak IPA |
|---|---|
| `1848` | `tˈiːsɔtʃ ˈoːsəmstɔ ˈoːsəminʃtˈiːridɛsɛt` ✓ |
| `tisoč osemsto oseminštirideset` | `tˈiːsɔtʃ ɔsˈeːmstɔ ɔsɛminʃtiridˈeːsɛt` ✗ (naglas na osémsto, …dését) |
| `36.500` | `ʃˈeːstintrˈiːdɛsɛt tˈiːsɔtʃ pˈeːtstɔ` ✓ |
| `šestintrideset tisoč petsto` | `ʃɛstintridˈeːsɛt …` ✗ |

eSpeak ima **poseben bralnik števil z ustreznim slovenskim naglasom**; ko mu daš
števnike kot besede, uporabi splošna pravila in naglasi napačno. Zato je naša
"popolna" normalizacija poslabšala prav tisto, kar je bilo prav.

## Rešitev: minimalni poseg

`normalize(..., minimal=True)` pusti pri miru vse, kar eSpeak že bere prav:

- cela števila in tisočice (`1848`, `36.500`) — bere pravilno
- odstotke (`65 %`) — pravilno
- `15 minut`, `3 ure` — pravilno
- popravi le: denar, datume, vrstilne številke, `°C`, `km/h`, okrajšave, rimske
  številke in **dvojino pri 2** (`2 uri` → `dve uri`, ker eSpeak reče "dva").

Preverjeno: `1848`, `36.500`, `65 %`, `15 minut`, `3 ure` ostanejo števke;
`št. 12 → številka 12`, `3. nadstropju → tretjem nadstropju`,
`14,80 evra → štirinajst evrov osemdeset centov`, `2 uri → dve uri`.

## Novi glasovi na strani

- **E** = B + minimalni popravki + imena
- **F** = B + minimalni popravki **brez** imen (da ločimo, ali slovar imen pomaga ali škodi)

Cevovod zdaj privzeto uporablja minimalni način; `--full-text` vrne starega.
Testi: 23 (dodani testi za minimalni način).


---

# Krog 9 — ritem in »avtotune« (28. 10. 2026)

Tvoja ocena: *»bolje, a nekatere besede še vedno izpljune prehitro; glas zveni
preveč avtotune.«*

## Ritem: kaj je bilo narobe

Sloleks verzija (G) je govorila vsako poved v enem kosu, s hitrostjo 1,0 in le
0,35 s med povedmi. Zato so se naštevani deli zlili.

**H** zdaj dela to:

| Meja | Premor |
|---|---|
| vejica | 0,16 s |
| podpičje/dvopičje | 0,22 s |
| konec povedi | 0,45 s (vprašanje 0,55 s) |
| konec odstavka | 0,85 s |

Poleg tega se hitrost spreminja z dolžino povedi (0,99–1,06), osnova pa je 1,02.
Trajanje se je zato podaljšalo za ~6–7 % (p1 28,2 → 30,1 s, p3 44,7 → 47,9 s).

**I** je H + nežna obdelava: blažji EQ (manj 2,6 kHz in 7,2 kHz), blaga
kompresija, mala soba, low-pass pri 12 kHz.

## »Avtotune«

To ni naglas in ne ritem — to je **vocoder 22 kHz VITS modela**. Spekter je
»kovinski« in F0 je skoraj konstanten; nobena nastavitev tega ne odpravi.
Možnosti so le:

1. **sprejeti** (H/I sta najboljše, kar ta model da),
2. **nežna obdelava** (I) — omili sijaj, ne spremeni barve,
3. **drug model** — Kokoro fine-tune ali plačljiv oblak.

## Poslušaj

Na strani so zdaj G (naglas), H (naglas + pavze) in I (H + mehka obdelava).
Primerjaj H z G za ritem in I s H za barvo.

---

# Krog 10 — ali obstaja lahka AI izboljšava glasu? (28. 10. 2026)

Da. Pregledal sem projekte in enega preizkusil.

| Projekt | Velikost | Licenca | Hitrost | Kaj naredi |
|---|---|---|---|---|
| **LavaSR** | 50 MB | Apache-2.0 | ~50× CPU | izboljšava govora, 8–48 kHz vhod |
| NovaSR | 52 KB | Apache-2.0 | ~3000× | 16k → 48k, nižja kakovost |
| Resemble Enhance | ~več 100 MB | MIT | počasneje | denoise + enhance |
| OpenVoice v2 | ~100 MB | MIT | srednje | menjava barve glasu (potreben vzorec) |
| RVC | ~1 GB | MIT | ~real-time | konverzija v ciljni glas (potreben model) |
| Seed-VC | ~500 MB | GPL-3.0 | počasneje | zero-shot konverzija glasu |
| AudioSR / FlashSR | 2–6 GB | MIT | 0,6–14× | difuzijska nadgradnja, pretežko |

## Preizkus: LavaSR na H

LavaSR sem pognal na H (naglas + pavze) za vse tri odlomke. Rezultat:

| | Središče spektra | F0 SD | Trajanje |
|---|---|---|---|
| H | 1,17 / 1,09 / 1,12 kHz | 5,5 | 30,1 s |
| **J (H + LavaSR)** | **0,97 / 0,96 / 0,98 kHz** | 5,4 | 30,1 s |

Torej: spekter se **ohladi** za ~15 %, trajanje in naglas ostaneta ista.
Nič ne doda »življenja« v melodijo — samo drugače obarva zvok.

## Sklep

Nobena od teh orodij ne odpravi »avtotune« značaja, ker je ta v vocoderju.
Lahke rešitve lahko:

- **omilijo sijaj** (LavaSR, Resemble Enhance),
- **zamenjajo barvo** (OpenVoice, RVC — a potrebujejo ciljni glas in pogosto
  dodajo svoje artefakte),
- **povečajo pasovno širino** (NovaSR — 16 kHz vhod, naša govorica je 22 kHz).

Prava sprememba ostaja **drug model** (Kokoro fine-tune) ali oblak.

Na strani je zdaj **J = H + LavaSR**; primerjaj H in J.
