# eSpeak-ng `sl`: kaj front-end res izgovori

Piper in Maya1 LoRA oba fonemizirata slovenščino skozi **eSpeak-ng `sl`**. Če je front-end napačen, je napačen tudi zvok — ne glede na to, kako dober je model.

**9 pravilnih, 1 delnih, 17 napačnih** od 27 primerov. Nabor je namenoma sestavljen iz težkih primerov, ne iz povprečnega besedila.

| Vhod | eSpeak IPA | Kar bi moral brati | Ocena | Opomba |
|---|---|---|---|---|
| `1848` | `tˈiːsɔtʃ ˈoːsəmstɔ ˈoːsəminʃtˈiːridɛsɛt` | tisoč osemsto oseminštirideset | ✓ |  |
| `1.278` | `tˈiːsɔtʃ dʋˈeːstɔ ˈoːsəminsˈeːdəmdɛsɛt` | tisoč dvesto oseminsedemdeset | ✓ |  |
| `36.500` | `ʃˈeːstintrˈiːdɛsɛt tˈiːsɔtʃ pˈeːtstɔ` | šestintrideset tisoč petsto | ✓ |  |
| `2024` | `dʋˈaː tˈiːsɔtʃ ʃtˈiːriindʋˈaːjsɛt` | dva tisoč štiriindvajset | ✓ |  |
| `8:30` | `ˈoːsəm trˈiːdɛsɛt` | osem trideset | ✓ |  |
| `3 ure` | `trˈiː ˈuːrɛ` | tri ure | ✓ |  |
| `20 %` | `dʋˈaːjsɛt ɔtstˈoːtkɔw` | dvajset odstotkov | ✓ |  |
| `65 %` | `pˈeːtinʃˈeːzddɛsɛt ɔtstˈoːtkɔw` | petinšestdeset odstotkov | ✓ | blaga asimilacija v 'šezddeset' |
| `14,80 evra` | `ʃtˈiːrinajst tsˌelih ˈoːsəmdɛsɛt ˈeːʋra` | štirinajst evrov osemdeset centov | ✗ | bere 'celih' |
| `3,5 kg` | `trˈiː tsˌelih pˈeːt kˌəɡˈə` | tri kilograme in pol | ✗ | bere 'celih' + črkovano enoto |
| `5 €` | `pˈeːt` | pet evrov | ✗ | valuta izgine |
| `2 kg` | `dʋˈaː kˌəɡˈə` | dva kilograma | ✗ | enota črkovana |
| `12 km/h` | `dʋˈaːnajst kˌəmˈə pɔʃˈeːwnitsa xˈə` | dvanajst kilometrov na uro | ✗ | črkovano + 'poševnica' |
| `21 °C` | `ˈɛːnaindʋˈaːjsɛt tsˈə` | enaindvajset stopinj Celzija | ✗ | bere 'ce' |
| `3. nadstropju` | `trˈiː natstrˈoːpju` | tretjem nadstropju | ✗ | vrstilni kot glavni |
| `19. stoletju` | `dˈɛʋˈeːtnajst stɔlˈeːtju` | devetnajstem stoletju | ✗ | vrstilni kot glavni |
| `5. poglavje` | `pˈeːt pɔɡlˈaːwjɛ` | peto poglavje | ✗ | vrstilni kot glavni |
| `II. del` | `dʋˈaː dˈeːw` | drugi del | ✗ | rimska kot glavni |
| `1. 5. 2024` | `ˈɛːna pˈeːt dʋˈaː tˈiːsɔtʃ ʃtˈiːriindʋˈaːjsɛt` | prvega maja dva tisoč štiriindvajset | ✗ | datum razstavljen |
| `št. 12` | `ʃˌətˈə dʋˈaːnajst` | številka dvanajst | ✗ | okrajšava nerazvozlana |
| `str. 5` | `stˈər pˈeːt` | stran pet | ✗ | okrajšava nerazvozlana |
| `dr. Novak` | `dˈər nˈoːʋak` | doktor Novak | ✗ | okrajšava nerazvozlana |
| `prof.` | `prˈoːf` | profesor | ~ | izgovori 'prof' |
| `npr.` | `nəpˈər` | na primer | ✗ | izgovori 'npr' |
| `itd.` | `ˈiːtt` | in tako dalje | ✗ | izgovori 'itd' |
| `t. i.` | `tˈə ˈiː` | tako imenovani | ✗ | črkovano |
| `A. Prešeren` | `ˈaː prɛʃˈeːrən` | A Prešeren | ✓ | začetnica kot črka |

## Kaj to pomeni

Glavne številke, letnice in ure eSpeak prebere prav. **Vrstilne številke, datumi, valuta, enote in okrajšave pa padejo** — natanko tisto, kar je v vsaki knjigi. Zato normalizacija ni 'dodatek za lepoto', ampak pogoj za uporaben posnetek.

Ta tabela je hkrati regresijski seznam za `norm_sl`: vsak ✗ mora po normalizaciji postati ✓.
