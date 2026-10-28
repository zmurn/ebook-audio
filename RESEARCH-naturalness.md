# Zakaj Piper zveni sintetično — in kaj to dejansko popravi

Raziskava, 26. 10. 2026. Vprašanje: *glas B je najbolj naraven, a ne vsebuje popravkov;
kako drugi sistemi rešujejo naravnost, lokalno?*

---

## 1. Kaj smo izmerili sami

| Poskus | Rezultat |
|---|---|
| `noise_w` 0,8 → 1,05 | gibanje F0 5,8 → 6,0 poltona — **nič** |
| EQ + kompresija + soba | središče spektra 1,15 → 1,07 kHz — **topleje, a enaka melodija** |
| tempo + pavze (V4) | ritem boljši, F0 nespremenjen |
| dih + nagib + šum (V5) | F0 SD 5,38 → 5,62 (+4 %) |

**Sklep: melodična revščina je v modelu, ne v nastavitvah.** Zato je tvoj instinkt pravilen —
B zveni najbolje, ker je neobdelan; naša obdelava je dodala barvo in ritem, ne pa življenja.

## 2. Kaj naredi TTS naraven

Naravnost ni ena stvar; sestavljena je iz štirih, po pomembnosti:

1. **Podatki** — količina in kakovost. Studiјski posnetki enega govorca, 20–50 h, z
   dosledno intonacijo. ARTUR ima 40 h enega govorca (G0911), studijsko.
2. **Arhitektura** — model mora imeti ločen **napovedovalnik prozodije** (trajanja, F0,
   energija) in **vocoder** (HiFi-GAN). VITS (Piper) to stisne v en model in je zato
   omejen; StyleTTS2/Kokoro in XTTS/F5 imajo prozodijo bolj eksplicitno.
3. **Stil / čustvo** — referenčni posnetek ali style embedding. Brez tega je glas
   "pripovedovalec z enim obrazom".
4. **Post-produkcija** — malo vpliva na naravnost, veliko na *vtis* (barva, prostor).

Naša obdelava je bila točka 4. Napredek je v točkah 1–3, torej v **drugem modelu**.

## 3. Kako to rešujejo drugi (in kaj je prenosljivo)

| Projekt | Pristop | Kaj se naučimo |
|---|---|---|
| **Kokoro-82M** | 82 M, Apache-2.0, StyleTTS2-osnova; "kakovost primerljiva z večjimi modeli" | majhen model + dobra arhitektura = naravnost brez GPU |
| **kikiri-tts** | reproducibilen recept za **nov jezik** na Kokoro: priprava podatkov → Stage 1 (multi-speaker baza) → Stage 2 (en govorec) → voicepack | 51 h nemške baze, nato 455–627 vzorcev za posamezen glas; teče na CPU |
| **Kokoro Bengali** (Zenodo, 2026) | 18,3 h enega govorca; espeak-ng foneme preslika v Kokorovih 178 simbolov; teacher-forced trening; **ground-truth F0/energija** v vocoder | 1.000–2.000 korakov zadošča za jasen govor; brez GT F0 nastane "muffled" govor |
| **Piper** | VITS; "high" = večji model pri 22,05 kHz | fine-tune obstoječega checkpointa je možen, a strop je arhitektura |
| **XTTS-v2** | 1,5 B, GPT + flow, zero-shot kloniranje, 17 jezikov | odlična prozodija, a počasen in trening je težji |
| **F5-TTS** | difuzijski, zelo naraven, fine-tuni za nove jezike (ruski, kurdski) | najboljša kakovost, najpočasnejši lokalno |
| **RVC** | konverzija glasu na posnetek človeka | spremeni **barvo**, ne prozodije — sam po sebi ne reši robotike |

Ključna ugotovitev iz tujih receptov: **za nov jezik ne potrebuješ velikega modela, ampak
(a) ~20–40 h dobrega enogovornega gradiva, (b) preslikavo espeak fonemov v modelov
slovar in (c) pravilno treniranje z ground-truth prozodijo.** ARTUR izpolnjuje (a);
slovenščina ima espeak glas za (b).

## 4. Možnosti, ocenjene za ta stroj (M1 Pro, 16 GB)

| Pot | Hitrost lokalno | Kakovost (potencial) | Podatki | Trening | Realno? |
|---|---|---|---|---|---|
| Piper medium (zdaj) | 10× | ★★☆ | — | nič | ✓ zdaj |
| Piper **high** fine-tune | 8–10× | ★★☆ (+malo) | 40 h | GPU 6–12 h | ✓ z najemom |
| **Kokoro-82M SL** | ~1–3× (ocena) | ★★★★ | 40 h | GPU 4–10 h | **✓ najbolj obetavno** |
| XTTS-v2 SL | 0,2–0,5× (ocena) | ★★★☆ | 40 h+ | GPU 10–20 h | ~ |
| F5-TTS SL | 0,05–0,1× (ocena) | ★★★★ | 20 h+ | GPU 10 h+ | ✗ za knjige |
| RVC na Piper | 1–5× | samo barva | 10 min glasu | 1–2 h | ~ dopolnilo |

Hitrosti za Kokoro/XTTS/F5 so ocene iz velikosti modelov, ne meritve na tem stroju.

## 5. Priporočeni načrt

**Zdaj (brez treninga):** obdrži **D** — B-jeve nastavitve + `norm_sl` + `pron_sl`, brez
EQ, sobe in tempa. To je najbolj naraven zvok s pravilnimi besedami. C (obdelava) ostane
kot opcija, ne privzeto.

**Naslednji resni korak (če želiš):** nauči **Kokoro-82M za slovenščino** na ARTUR 40 h.

1. Priprava: ARTUR (en govorec, studijsko) → 24 kHz, tekst + fonemi prek espeak `sl`.
2. Preslikava fonemov v Kokorov slovar (178 simbolov); preveri `ə, ʋ, ɲ, ʎ, tʃ, dʒ`.
3. Stage 1 na celotnem ARTUR (ali na kikiri nemški bazi kot initialize).
4. Stage 2 na enem govorcu (G0911) — 500–1.000 vzorcev.
5. Izvoz voicepacka; inference lokalno.
6. Evalvacija: iste tri odlomke + 10-minutno poglavje; primerjava z D.

**Stroški:** najem ene GPU (A100/4090) za 4–10 h ≈ **$10–40**. Čas: 1–2 dni dela
(priprava podatkov je večino tega). Rezultat teče lokalno in je hitrejši od XTTS.

**Tveganja:** Kokorov vocoder je treniran na 24 kHz angleščini; slovenski fonemi, ki jih
ni v slovarju, se morajo preslikati (npr. `ʋ → v`, `ʎ → lj`). ARTUR je bralni, ne
literarni govor — prozodija bo boljša od Piperjeve, a morda še vedno "poročevalska".
Ni garancije za MOS; to je eksperiment, ne nakup.

## 6. Kaj ostaja nespremenjeno

`norm_sl` in `pron_sl` sta neodvisna od modela — ob menjavi modela ostaneta in se
preneseta. Prav tako `pipeline.py` (EPUB → M4B). Zamenja se samo `Engine` za sintezo.

## Viri

- Kokoro-82M: <https://github.com/hexgrad/kokoro>
- kikiri-tts (Kokoro za nov jezik): <https://github.com/semidark/kikiri-tts>
- Kokoro Bengali, teacher-forced recept: <https://zenodo.org/records/22789547>
- Piper trening: <https://github.com/rhasspy/piper/blob/master/TRAINING.md>
- ARTUR 40 h (en govorec): <https://huggingface.co/datasets/ppisljar/artur_studio_tts>
- Premori in dih v zvočnih knjigah: <https://www.isca-archive.org/interspeech_2012/bailly12_interspeech.html>
