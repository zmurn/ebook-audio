# Slovenian pronunciation data and the engine decision

Research note, 28. 10. 2026. Question: can we get authoritative Slovenian
pronunciation (fran.si), should we bolt it onto Piper, or is ElevenLabs the
better answer?

---

## 1. fran.si: good reference, not a data source

[Fran](https://fran.si/) is the ZRC SAZU dictionary portal: SSKJ², eSSKJ, Sprotni
slovar, Pravopis 8.0 and more. Entries show stress and pronunciation notes, and
[Pravopis 8.0](https://pravopis8.fran.si/) has explicit chapters on how letters
and letter clusters are pronounced.

But its [terms of use](https://fran.si/o-portalu?page=Terms) say:

> »Avtomatsko pridobivanje večjih količin podatkov je dovoljeno ob pisnem soglasju
> ZRC SAZU.«

Bulk automated extraction needs written permission, and `robots.txt` disallows
`/iskanje/`. There is no API. So fran.si is for **human spot checks**, not for
building a lexicon. Asking ZRC SAZU for consent is possible but slow.

## 2. Sloleks 2.0: the machine-readable source (with a catch)

[Sloleks 2.0](http://hdl.handle.net/11356/1230) is the reference morphological
lexicon from the same institute: ~100,000 lemmas and their inflected forms, in
LMF XML (46 MB zipped, **1.3 GB unpacked**).

Each word form carries:

```xml
<feat att="zapis_oblike" val="beseda"/>
<feat att="naglašena_beseda_1" val="beséda"/>   <!-- stress, manually corrected -->
<feat att="SAMPA_1" val="bE&quot;se:da"/>        <!-- auto-generated -->
<feat att="IPA_1" val="bɛˈseːda"/>             <!-- auto-generated -->
```

That is exactly the pronunciation dictionary we wanted. **License: CC BY-NC-SA
4.0** — free for personal use, not for commercial distribution, and share-alike.

### The catch: the IPA is not trustworthy for stress

The record says accents are "automatically assigned … and partially manually
corrected", while IPA and SAMPA are "automatically generated". In the data the
two disagree, and the accented spelling is the one that is right:

| Word | accented form (manual) | IPA (auto) | Slovenian actually says |
|---|---|---|---|
| Cankar | `Cánkar` | `tsaŋˈkar` | **CÁN**-kar ✓ accent is right |
| Mozart | `Mózart` | `mɔˈzaːrt` | **MÓ**-cart ✓ accent is right |
| Bregović | `Bregović` | `brɛɡɔvić` | no stress mark at all |
| beseda | `beséda` | `bɛˈseːda` | be-SÉ-da ✓ both agree |

Two consequences:

1. **Use `naglašena_beseda_1` for stress, not `IPA_1`.** The accent marks (á, é,
   ê, ò …) are the reliable part.
2. **Foreign names are not adapted.** Sloleks gives `mɔˈzaːrt` — [z], not [ts],
   and the wrong stress. Our respelling lexicon (`Mozart → Mocart`,
   `Bregović → Bre-gović`) remains better for names.

So the division of labour is: Sloleks for **native vocabulary stress**, our
`pron_sl` for **foreign names**, `norm_sl` for numbers and abbreviations.

## 3. Can Piper actually use IPA? Yes — proven

Piper's CLI cannot, but its Python API can synthesize from phoneme IDs:

```python
voice = PiperVoice.load("sl_SI-artur-medium.onnx", config_path="...json")
ids = voice.phonemes_to_ids(["b", "ɛ", "ˈ", "s", "e", "ː", "d", "a"])
audio = voice.phoneme_ids_to_audio(ids, SynthesisConfig())   # numpy array
```

Measured: `beseda` from Sloleks IPA → 0.81 s of audio. The voice's alphabet has
157 symbols including `ˈ`, `ˌ`, `ː`, `ɛ`, `ɔ`, `ə`, `ʋ`, `ɲ`, `ʎ`, `tʃ`, `dʒ`.

Gaps to bridge (small):

| Sloleks / IPA | Piper alphabet | Fix |
|---|---|---|
| `eː`, `oː`, `aː` | `e`+`ː`, `o`+`ː` | split the length mark |
| `tɕ`, `dʑ` | `tʃ`, `dʒ` (or `t`+`ɕ`) | map affricates |
| `ɡ` vs `g` | `ɡ` exists | keep |

After that, stress is exact, on any word Sloleks knows. That is a real
improvement over eSpeak's guessing — but it does **not** change the voice's
timbre. The robotic quality stays.

## 4. ElevenLabs: Slovenian is supported, and it takes IPA

- Slovenian (`sl`) is on the **Eleven v4** language list, 90+ languages.
- **Professional Voice Cloning** supports every v4 language; 30–180 minutes of
  audio. ARTUR has 40 hours, but cloning that narrator raises consent/licence
  questions. Cloning your own voice is clean.
- **Pronunciation dictionaries** accept IPA; phoneme tags work on `eleven_v4`,
  `v4_turbo`, `flash_v2` and `v3`. Non-English IPA requires setting the
  dictionary language.

Pricing (published plans, 28. 10. 2026; 1 credit ≈ 1 character on the
highest-quality models, ~1,000 characters ≈ 1 minute of audio):

| Plan | Price | Credits | ≈ per book |
|---|---|---|---|
| Free | $0 | 10,000 | ~10 min audio — enough for a test |
| Creator | $22/mo | 121,000 | ~$109 (needs 5 months) |
| **Pro** | **$99/mo** | **600,000** | **~$99 for one 10 h book** |
| Scale | $299/mo | 1,800,000 | ~$100/book, 3 books |
| Business | $990/mo | 6,000,000 | ~$99/book, 10 books |

So a novel costs **~$100** at ElevenLabs, versus ~$10–15 at Google Chirp 3 or
Azure. Whether that gap is worth it in **Slovenian** is exactly what a 10-minute
free-tier test would answer.

## 5. Recommendation

**Do not scrape fran.si.** Use Sloleks (licensed, same institute, has stress),
and keep fran.si for manual checks.

**If staying local:** build the lookup layer —
`wordform → naglašena_beseda → stress position → Piper IPA ids`,
with `pron_sl` overriding foreign names and `norm_sl` handling numbers.
Effort: 1–2 days (mostly parsing 1.3 GB XML into a compact TSV, ~100–150 MB).
Result: exact stress on native words, unchanged timbre.

**If quality matters more than privacy:** test ElevenLabs v4 first.
The free tier gives ~10,000 characters, roughly ten minutes — enough for the
same three passages plus a chapter. Feed it:
`language_code="sl"`, a v4 model, and an IPA dictionary built from our existing
`pron_sl` entries. If it clearly beats D/F, the ~$100/book is the honest price
of "sounds real".

**Hybrid (my recommendation):** keep Piper + Sloleks for drafts and previews
(free, instant), use ElevenLabs only for the final render of books worth
keeping. The text layer — `norm_sl`, `pron_sl`, chapter extraction — is
engine-independent and already built, so the switch costs one adapter.

## What I would do next, in order

1. Build a 10-minute ElevenLabs test (free tier) with the three passages.
2. Build the Sloleks → stress-TSV converter, even if we go cloud: it improves
   the IPA dictionary we send to ElevenLabs too.
3. Only then decide whether the local path gets more engineering.

## Sources

- Fran terms of use: <https://fran.si/o-portalu?page=Terms>
- Pravopis 8.0: <https://pravopis8.fran.si/>
- Sloleks 2.0: <http://hdl.handle.net/11356/1230> (CC BY-NC-SA 4.0)
- ElevenLabs v4 languages + PVC: <https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/what-languages-are-supported-with-professional-voice-cloning-pvc>
- ElevenLabs pronunciation dictionaries: <https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries>
- ElevenLabs pricing: <https://elevenlabs.io/pricing>


---

## 6. What was built (100% local, 0 €)

The paid route was dropped. Instead:

- `scripts/build_sloleks_stress.py` → **888,148 word forms**, 5.9 MB gzip table.
  **8,259 forms (0.9 %) are homographs** with different stress (`samo/samó/sámo`,
  `vratu/vratú/vrátu`) and are skipped rather than guessed.
- `sl_stress.py` moves the stress mark in Piper's phonemes to the Sloleks syllable.
- `stress_tts.py` phonemises the whole sentence with eSpeak (so `vleklo → ulˈeːklɔ`
  allophony and punctuation survive), splits at word boundaries, and only edits
  the stress mark before synthesising from phoneme IDs.
- Wired into the pipeline (`--stress`) and the app (checkbox **Sloleks naglas**).

Measured on the test passages: 13 stress corrections per ~50 words on p1
(`travnikov`, `vstajajo`, `zgodaj`, `ljudje`, `nasmehnila` …), 13 on p3, 4 on p2.
eSpeak is already right on many common words; the gains are in less frequent and
inflected forms.

Rejected: synthesising **word by word**. It preserved stress but degraded the
phoneme stream (ASR coverage 60 % vs 58 % baseline, visibly garbled transcript),
so sentence-level phonemes with in-place stress editing won.

Known limits: Sloleks does not stress every foreign name (`Bregović` has no
accent), so `pron_sl` still handles those; and if the word count does not align
with eSpeak's chunks, that sentence is left untouched.
