# Rezultati meritve — slovenski bake-off

Objektivne meritve so samo preverjanje razumljivosti in glasnosti. Naravnost in naglas se ne merita — to presodi uho.

| Glas | Prehod | Trajanje | Znakov/s | LUFS | Peak dBFS | Tišina | Pavze >0,8 s |
|---|---|---|---|---|---|---|---|
| apple_tina | p1_narrative | 24.74 s | 16.2 | -18.9 | -3.9 | 0.0% | 0 |
| apple_tina | p2_dialogue | 20.55 s | 16.5 | -18.8 | -4.8 | 0.0% | 0 |
| apple_tina | p3_numbers | 41.79 s | 10.8 | -18.9 | -3.0 | 0.0% | 0 |
| piper_artur | p1_narrative | 27.1 s | 14.8 | -18.9 | -3.0 | 8.9% | 0 |
| piper_artur | p2_dialogue | 23.46 s | 14.5 | -18.9 | -3.0 | 13.4% | 0 |
| piper_artur | p3_numbers | 46.02 s | 9.8 | -18.9 | -3.0 | 7.8% | 0 |
| piper_min | p3_numbers | 42.95 s | 10.5 | -19.5 | -3.0 | 1.0% | 0 |
| piper_min_nopron | p3_numbers | 43.15 s | 10.5 | -18.9 | -3.0 | 1.0% | 0 |
| piper_norm | p3_numbers | 49.82 s | 9.1 | -19.0 | -3.0 | 9.9% | 1 |
| piper_textfix | p3_numbers | 43.04 s | 10.5 | -18.9 | -3.0 | 0.0% | 0 |

## Glasovi

- **Apple · Tina (sl_SI)** — macOS sistemski glas, sistemski. Že nameščen na tem Macu; brezplačen, a ne prilagodljiv.
- **Piper · sl_SI-artur-medium** — VITS (ONNX, CPU), ~63 MB. Edini vnaprej pripravljen slovenski glas, ki teče na CPU brez GPU.
- **Piper · B + minimalni popravki** — VITS, minimalna normalizacija + imena, 63 MB. Številke kot števke, popravljene le napake.
- **Piper · B + minimalni popravki brez imen** — VITS, minimalna normalizacija, 63 MB. Brez izgovornega slovarja.
- **Piper · artur + norm_sl + pron_sl** — VITS + normalizacija + izgovorni slovar + tempo, 63 MB. Isti glas kot piper_artur, le besedilo je normalizirano (samo p3).
- **Piper · B + norm_sl + pron_sl** — VITS, brez obdelave, 63 MB. Iste nastavitve kot B, le besedilo je popravljeno.
