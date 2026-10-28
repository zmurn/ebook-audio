# Rezultati meritve — slovenski bake-off

Objektivne meritve so samo preverjanje razumljivosti in glasnosti. Naravnost in naglas se ne merita — to presodi uho.

| Glas | Prehod | Trajanje | Znakov/s | LUFS | Peak dBFS | Tišina | Pavze >0,8 s |
|---|---|---|---|---|---|---|---|
| apple_tina | p1_narrative | 24.74 s | 16.2 | -18.9 | -3.9 | 0.0% | 0 |
| apple_tina | p2_dialogue | 20.55 s | 16.5 | -18.8 | -4.8 | 0.0% | 0 |
| apple_tina | p3_numbers | 41.79 s | 10.8 | -18.9 | -3.0 | 0.0% | 0 |
| maya1_lora | p1_narrative | 23.98 s | 16.7 | -19.0 | -2.9 | 19.3% | 3 |
| piper_artur | p1_narrative | 27.1 s | 14.8 | -18.9 | -3.0 | 8.9% | 0 |
| piper_artur | p2_dialogue | 23.46 s | 14.5 | -18.9 | -3.0 | 13.4% | 0 |
| piper_artur | p3_numbers | 46.02 s | 9.8 | -18.9 | -3.0 | 7.8% | 0 |
| piper_min | p3_numbers | 42.95 s | 10.5 | -19.5 | -3.0 | 1.0% | 0 |
| piper_min_nopron | p3_numbers | 43.15 s | 10.5 | -18.9 | -3.0 | 1.0% | 0 |
| piper_norm | p3_numbers | 44.93 s | 10.1 | -19.0 | -3.0 | 4.8% | 0 |
| piper_stress | p1_narrative | 28.21 s | 14.2 | -19.0 | -3.0 | 9.7% | 0 |
| piper_stress | p2_dialogue | 22.94 s | 14.8 | -18.9 | -3.0 | 13.6% | 0 |
| piper_stress | p3_numbers | 44.72 s | 10.1 | -18.9 | -3.0 | 6.0% | 0 |
| piper_textfix | p3_numbers | 43.04 s | 10.5 | -18.9 | -3.0 | 0.0% | 0 |
| piper_v1 | p1_narrative | 26.63 s | 15.1 | -18.9 | -3.0 | 7.9% | 0 |
| piper_v1 | p2_dialogue | 22.53 s | 15.1 | -18.9 | -3.0 | 11.8% | 0 |
| piper_v2 | p1_narrative | 28.6 s | 14.0 | -18.9 | -3.0 | 7.7% | 0 |
| piper_v2 | p2_dialogue | 25.75 s | 13.2 | -18.7 | -3.4 | 11.4% | 0 |
| piper_v3 | p1_narrative | 28.63 s | 14.0 | -18.9 | -3.2 | 6.7% | 0 |
| piper_v3 | p2_dialogue | 24.25 s | 14.0 | -18.8 | -3.8 | 11.1% | 0 |
| piper_v4 | p1_narrative | 29.91 s | 13.4 | -18.9 | -3.4 | 12.0% | 1 |
| piper_v4 | p2_dialogue | 25.18 s | 13.5 | -18.8 | -3.8 | 15.3% | 1 |
| piper_v5 | p1_narrative | 31.99 s | 12.5 | -18.9 | -3.0 | 17.9% | 5 |
| piper_v5 | p2_dialogue | 28.02 s | 12.1 | -18.8 | -3.4 | 13.1% | 3 |

## Glasovi

- **Apple · Tina (sl_SI)** — macOS sistemski glas, sistemski. Že nameščen na tem Macu; brezplačen, a ne prilagodljiv.
- **Maya1 · slovenski LoRA** — 3B speech-LM + SNAC (GPU/CPU), ~6 GB. Isti govorec (ARTUR G0911) kot Piper, druga arhitektura.
- **Piper · sl_SI-artur-medium** — VITS (ONNX, CPU), ~63 MB. Edini vnaprej pripravljen slovenski glas, ki teče na CPU brez GPU.
- **Piper · B + minimalni popravki** — VITS, minimalna normalizacija + imena, 63 MB. Številke kot števke, popravljene le napake.
- **Piper · B + minimalni popravki brez imen** — VITS, minimalna normalizacija, 63 MB. Brez izgovornega slovarja.
- **Piper · artur + norm_sl + pron_sl** — VITS + normalizacija + izgovorni slovar + tempo, 63 MB. Isti glas kot piper_artur, le besedilo je normalizirano (samo p3).
- **Piper · Sloleks naglas** — VITS + Sloleks naglas, 63 MB + 5,9 MB tabele. Naglas iz slovarske baze, brez oblaka.
- **Piper · B + norm_sl + pron_sl** — VITS, brez obdelave, 63 MB. Iste nastavitve kot B, le besedilo je popravljeno.
- **piper_v1** — ?, ?. 
- **piper_v2** — ?, ?. 
- **piper_v3** — ?, ?. 
- **piper_v4** — ?, ?. 
- **piper_v5** — ?, ?. 
