# Razumljivost (povratni ASR)

Whisper `openai/whisper-small`, jezik `sl`. Referenca za p3 je **izgovorjena oblika** (številke izpisane z besedo), sicer bi vsak sistem izgledal napačno.

| Glas | Prehod | WER | CER |
|---|---|---|---|
| apple_tina | p1_narrative | 37.5% | 4.7% |
| apple_tina | p2_dialogue | 29.0% | 4.5% |
| apple_tina | p3_numbers | 59.6% | 43.8% |
| piper_artur | p1_narrative | 37.5% | 6.3% |
| piper_artur | p2_dialogue | 33.9% | 5.3% |
| piper_artur | p3_numbers | 69.1% | 64.6% |
