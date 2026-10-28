#!/usr/bin/env python3
"""Build the self-contained bake-off listening page.

Reads passages.json + metrics.json, assigns blind labels, and writes
bakeoff/index.html. Voice names stay hidden until the listener reveals them,
so the score is about the sound, not the logo.

Usage: python3 scripts/build_page.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAKEOFF = ROOT / "bakeoff"

VOICES = {
    "apple_tina": {
        "name": "Apple · Tina",
        "meta": "macOS sistemski glas · brezplačen, že nameščen",
    },
    "piper_min": {
        "name": "Piper · B + minimalni popravki",
        "meta": "številke pustimo eSpeaku (boljši naglas), popravimo le napake + imena",
        "always": True,
    },
    "piper_pace": {
        "name": "Piper · Sloleks + pavze",
        "meta": "naglas + premori na vejicah, brez obdelave",
        "always": True,
    },
    "piper_lava": {
        "name": "Piper · H + LavaSR",
        "meta": "H, nato AI izboljšava govora (LavaSR, 50 MB, Apache-2.0)",
        "always": True,
    },
    "piper_pace_soft": {
        "name": "Piper · Sloleks + pavze + mehka obdelava",
        "meta": "kot H, z nežnim EQ, kompresijo in malo sobe",
        "always": True,
    },
    "piper_stress": {
        "name": "Piper · Sloleks naglas",
        "meta": "naglas iz slovarske baze Sloleks (brezplačno, lokalno)",
        "always": True,
    },
    "piper_min_nopron": {
        "name": "Piper · B + minimalni popravki, brez imen",
        "meta": "kot E, a imena ostanejo taka, kot jih bere eSpeak",
        "always": True,
    },
    "piper_textfix": {
        "name": "Piper · B + norm_sl + pron_sl",
        "meta": "iste nastavitve kot B, le besedilo je popravljeno (brez obdelave)",
        "always": True,
    },
    "piper_artur": {
        "name": "Piper · artur-medium",
        "meta": "VITS, 63 MB · teče na CPU",
    },
    "piper_norm": {
        "name": "Piper · artur + norm_sl + pron_sl",
        "meta": "isti glas kot B: številke, imena, tempo in mala soba (samo p3)",
        "always": True,
    },
    "maya1_lora": {
        "name": "Maya1 · slovenski LoRA",
        "meta": "3B speech-LM, ~6 GB · GPU priporočen",
    },
}

CRITERIA = [
    ("izgovor", "Izgovorjava", "Ali so besede, šumniki, imena in številke pravilno prebrani?"),
    ("naravnost", "Naravnost", "Zveni kot človek, ki bere — ali kot stroj, ki izgovarja?"),
    ("utrujenost", "Vzdrži 10 ur", "Bi to poslušal še po treh urah? (1 = ne, 5 = z lahkoto)"),
    ("knjiga", "Primerno za knjigo", "Ali bi to bil tvoj izbor za roman?"),
]


def main() -> None:
    passages = json.loads((BAKEOFF / "passages" / "passages.json").read_text())
    metrics = json.loads((BAKEOFF / "metrics.json").read_text())

    # Which voice/passage pairs actually rendered.
    rendered = {(m["voice"], m["passage"]) for m in metrics}
    voices = [v for v in VOICES if any((v, p["id"]) in rendered for p in passages)]

    # Fixed blind shuffle: label order must not correlate with plausibility.
    # stable labels: A/B/C keep the names earlier rounds used, D is the new one
    LABELS = {"apple_tina": "A", "piper_artur": "B", "piper_norm": "C",
              "piper_textfix": "D", "piper_min": "E", "piper_min_nopron": "F",
              "piper_stress": "G", "piper_pace": "H", "piper_pace_soft": "I",
              "piper_lava": "J"}
    voices = sorted(voices, key=lambda v: LABELS.get(v, "Z"))
    labels = {v: LABELS.get(v, chr(65 + i)) for i, v in enumerate(voices)}

    durations = {(m["voice"], m["passage"]): m["duration_s"] for m in metrics}
    data = {
        "passages": passages,
        "durations": {v: {p["id"]: durations[(v, p["id"])] for p in passages if (v, p["id"]) in durations} for v in voices},
        "voices": [
            {
                "id": v,
                "label": labels[v],
                "name": VOICES[v]["name"],
                "meta": VOICES[v]["meta"],
                "always": VOICES[v].get("always", False),
                "files": {
                    p["id"]: f"norm/{v}/{p['id']}.wav"
                    for p in passages
                    if (v, p["id"]) in rendered
                },
            }
            for v in voices
        ],
        "criteria": [{"id": c[0], "label": c[1], "hint": c[2]} for c in CRITERIA],
    }

    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    (BAKEOFF / "index.html").write_text(html)
    print(f"wrote {BAKEOFF/'index.html'} — {len(voices)} voices, {len(passages)} passages")


TEMPLATE = r"""<!doctype html>
<html lang="sl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slovenski glasovi — slepi test</title>
<style>
  :root {
    --paper: #f6f3ee;
    --ink: #1b1a18;
    --muted: #6b655d;
    --rule: #d9d2c7;
    --accent: #a4441f;
    --accent-soft: #f0e2d9;
    --ok: #2f6b4f;
    --card: #fffdfa;
    --radius: 10px;
    --shadow: 0 1px 2px rgba(27,26,24,.06), 0 8px 24px -16px rgba(27,26,24,.35);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #141312;
      --ink: #ece7df;
      --muted: #a49b8f;
      --rule: #33302c;
      --accent: #e08a5f;
      --accent-soft: #2b211b;
      --ok: #7fbf9c;
      --card: #1c1a18;
      --shadow: 0 1px 2px rgba(0,0,0,.4);
    }
  }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font: 16px/1.55 -apple-system, "Segoe UI", Inter, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  main { max-width: 940px; margin: 0 auto; padding: 56px 24px 96px; }
  header { border-bottom: 1px solid var(--rule); padding-bottom: 28px; margin-bottom: 40px; }
  .eyebrow {
    font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
    color: var(--accent); font-weight: 650; margin: 0 0 12px;
  }
  h1 { font-size: clamp(28px, 4.4vw, 40px); line-height: 1.1; letter-spacing: -.02em; margin: 0 0 12px; font-weight: 600; }
  .lede { color: var(--muted); max-width: 62ch; margin: 0; }
  .lede b { color: var(--ink); font-weight: 600; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .1em; color: var(--muted); font-weight: 650; margin: 40px 0 16px; }
  .passage { background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; margin-bottom: 20px; }
  .passage-head { padding: 18px 20px 0; }
  .passage-head h3 { margin: 0 0 4px; font-size: 17px; font-weight: 620; letter-spacing: -.01em; }
  .passage-head p { margin: 0; color: var(--muted); font-size: 13.5px; }
  .text {
    margin: 14px 20px 18px; padding: 14px 16px; background: var(--paper);
    border-left: 2px solid var(--accent); border-radius: 0 6px 6px 0;
    font-size: 14.5px; line-height: 1.6; color: var(--ink); white-space: pre-wrap;
  }
  .rows { border-top: 1px solid var(--rule); }
  .row {
    display: grid; grid-template-columns: 92px 1fr auto; align-items: center; gap: 14px;
    padding: 12px 20px; border-bottom: 1px solid var(--rule);
  }
  .row:last-child { border-bottom: 0; }
  .row.playing { background: var(--accent-soft); }
  .badge {
    display: inline-grid; place-items: center; width: 34px; height: 34px; border-radius: 50%;
    background: var(--ink); color: var(--paper); font-weight: 700; font-size: 15px;
    font-variant-numeric: tabular-nums;
  }
  .row.playing .badge { background: var(--accent); }
  .who { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .who .name { font-size: 13px; color: var(--muted); }
  .who .name b { color: var(--ink); font-weight: 600; }
  .who .name .meta { display: block; font-size: 12px; color: var(--muted); }
  .revealed .who .name b { color: var(--accent); }
  .dur { font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted); }
  button {
    font: inherit; cursor: pointer; border-radius: 8px; border: 1px solid var(--rule);
    background: var(--card); color: var(--ink); padding: 7px 13px; transition: background .15s, border-color .15s;
  }
  button:hover { border-color: var(--muted); }
  button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .play { display: inline-flex; align-items: center; gap: 7px; min-width: 96px; justify-content: center; }
  .play svg { width: 12px; height: 12px; fill: currentColor; }
  .row.playing .play { background: var(--accent); border-color: var(--accent); color: #fff; }
  .probe { margin: 8px 0 34px; border: 1px solid var(--rule); border-radius: var(--radius); background: var(--card); padding: 0 18px; }
  .probe summary { cursor: pointer; padding: 14px 0; font-size: 14px; font-weight: 600; }
  .probe summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
  .probe .hint { margin: 0 0 12px; }
  .probe-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 8px 0 14px; font-size: 13px; color: var(--muted); }
  .probe-row audio { height: 34px; flex: 1; min-width: 260px; }
  .toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0 34px; }
  .toolbar .primary { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .score { background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
  .score-row { display: grid; grid-template-columns: 64px repeat(4, 1fr); gap: 10px; padding: 12px 20px; border-bottom: 1px solid var(--rule); align-items: start; }
  .score-row:last-of-type { border-bottom: 0; }
  .score-head { padding: 14px 20px; border-bottom: 1px solid var(--rule); display: grid; grid-template-columns: 64px repeat(4, 1fr); gap: 10px; }
  .score-head div { font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); font-weight: 650; }
  .score-head div span { display: block; text-transform: none; letter-spacing: 0; font-weight: 400; font-size: 11.5px; line-height: 1.3; margin-top: 3px; color: var(--muted); }
  .seg { display: flex; gap: 4px; }
  .seg label { flex: 1; }
  .seg input { position: absolute; opacity: 0; pointer-events: none; }
  .seg span {
    display: grid; place-items: center; height: 34px; border: 1px solid var(--rule);
    border-radius: 6px; font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted);
    background: var(--paper);
  }
  .seg label:hover span { border-color: var(--muted); color: var(--ink); }
  .seg input:checked + span { background: var(--ink); border-color: var(--ink); color: var(--paper); font-weight: 650; }
  .seg input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
  textarea {
    width: 100%; margin: 14px 0 0; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--rule);
    background: var(--paper); color: var(--ink); font: inherit; font-size: 14px; resize: vertical; min-height: 76px;
  }
  textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .status { min-height: 22px; font-size: 13px; color: var(--ok); margin-top: 10px; }
  footer { margin-top: 56px; padding-top: 20px; border-top: 1px solid var(--rule); font-size: 13px; color: var(--muted); }
  footer a { color: var(--accent); }
  .hint { font-size: 13px; color: var(--muted); margin: 0 0 14px; }
  @media (max-width: 720px) {
    .score-head { display: none; }
    .score-row { grid-template-columns: 1fr; gap: 6px; }
    .score-row > .crit { font-size: 12.5px; color: var(--muted); }
    .row { grid-template-columns: 44px 1fr; }
    .row .dur { display: none; }
    .row .play { grid-column: 2; justify-self: start; }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">Slepi test · slovenski glasovi</p>
    <h1>Kateri glas zdrži deset ur?</h1>
    <p class="lede">
      Trije odlomki, isti za vsak glas. Imena so skrita, dokler jih ne razkriješ — da ne izbiraš
      po znanem imenu. <b>B</b> je neobdelan. <b>C</b> = B + popravljeno besedilo + tempo in soba.
      <b>D</b> = B + popravljeno besedilo, <b>brez obdelave</b> — primerjaj B, D in C zaporedoma.
      Ocene se shranijo v brskalniku.
    </p>
  </header>

  <div class="toolbar">
    <button id="reveal" aria-pressed="false">Razkrij imena</button>
    <button id="reset">Počisti ocene</button>
  </div>

  <audio id="player" preload="none"></audio>

  <div id="passages"></div>

  <details class="probe">
    <summary>Maya1 (3B) — referenca, ni v ocenjevanju</summary>
    <p class="hint">Ista zgodba, dvakrat: kratka poved uspe, daljši odlomek se začne ponavljati.
      Meritve in prepis v <a href="FINDINGS.md">FINDINGS.md</a>.</p>
    <div class="probe-row"><span>Kratka poved · 4,9 s</span>
      <audio controls preload="none" src="out/maya1_lora/p1_short.wav"></audio></div>
    <div class="probe-row"><span>Cel odlomek · 24 s, degradiran</span>
      <audio controls preload="none" src="out/maya1_lora/p1_narrative.wav"></audio></div>
  </details>

  <details class="probe">
    <summary>Zveni robotsko? Tri različice istega glasu (p1)</summary>
    <p class="hint">Isti model, ista poved, ista glasnost. <b>V1</b> = osnovno. <b>V3</b> = toplejši EQ,
      blaga kompresija, mala soba. <b>V4</b> = V3 + spremenljiv tempo in pavze po tipu povedi. <b>V5</b> = V4 + dihanje
      na pavzah, počasen nagib tona in neprekinjen prostorski šum.
      Gibanje višine je pri vseh treh enako (5,2–5,7 poltona) — razlika je v barvi in ritmu.</p>
    <div class="probe-row"><span>V1 · osnovno</span>
      <audio controls preload="none" src="out/piper_v1/p1_narrative.wav"></audio></div>
    <div class="probe-row"><span>V3 · topleje + soba</span>
      <audio controls preload="none" src="out/piper_v3/p1_narrative.wav"></audio></div>
    <div class="probe-row"><span>V4 · + tempo in pavze</span>
      <audio controls preload="none" src="out/piper_v4/p1_narrative.wav"></audio></div>
    <div class="probe-row"><span>V5 · + dihanje, ton, soba</span>
      <audio controls preload="none" src="out/piper_v5/p1_narrative.wav"></audio></div>
  </details>

  <h2>Ocena</h2>
  <p class="hint">1 = slabo, 5 = odlično. Ocenjuj glas, ne odlomka.</p>
  <div class="score" id="score"></div>
  <textarea id="notes" placeholder="Opombe: kje je naglas narobe, kje zastane, kaj te moti …"></textarea>
  <div class="status" id="status" role="status" aria-live="polite"></div>
  <div class="toolbar" style="margin-top:18px">
    <button class="primary" id="export">Kopiraj povzetek</button>
    <button id="download">Prenesi JSON</button>
  </div>

  <footer>
    Meritve (trajanje, glasnost, hitrost govora) so v
    <a href="results.md">results.md</a> — odpri šele po poslušanju.
  </footer>
</main>
<script>
const DATA = __DATA__;
const KEY = "sl-bakeoff-v1";
let state = JSON.parse(localStorage.getItem(KEY) || "{}");
state.scores ??= {};
state.notes ??= "";

const player = document.getElementById("player");
const passagesEl = document.getElementById("passages");
let activeRow = null;

function stop() {
  player.pause();
  if (activeRow) activeRow.classList.remove("playing");
  activeRow = null;
}

for (const p of DATA.passages) {
  const sec = document.createElement("section");
  sec.className = "passage";
  sec.innerHTML = `
    <div class="passage-head">
      <h3>${p.label}</h3>
      <p>${p.why}</p>
    </div>
    <div class="text">${p.text.replace(/&/g,"&amp;").replace(/</g,"&lt;")}</div>
    <div class="rows"></div>`;
  const rows = sec.querySelector(".rows");

  for (const v of DATA.voices) {
    const file = v.files[p.id];
    if (!file) continue;
    const row = document.createElement("div");
    row.className = "row";
    row.dataset.voice = v.id;
    row.innerHTML = `
      <span class="badge" aria-hidden="true">${v.label}</span>
      <div class="who">
        <button class="play" data-src="${file}" aria-label="Predvajaj glas ${v.label}, ${p.label}">
          <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 1.5v9l8-4.5z"/></svg>
          <span>Poslušaj</span>
        </button>
        <span class="name">Glas ${v.label}<b class="real" ${v.always ? "" : "hidden"}> · ${v.name}</b>
          <span class="meta real" ${v.always ? "" : "hidden"}>${v.meta}</span>
        </span>
      </div>
      <span class="dur">${(DATA.durations[v.id] && DATA.durations[v.id][p.id]) ? DATA.durations[v.id][p.id].toFixed(1) + " s" : ""}</span>`;
    const btn = row.querySelector(".play");
    btn.addEventListener("click", () => {
      if (activeRow === row && !player.paused) { stop(); return; }
      stop();
      player.src = file;
      player.play();
      row.classList.add("playing");
      activeRow = row;
    });
    rows.appendChild(row);
  }
  passagesEl.appendChild(sec);
}

player.addEventListener("ended", stop);

// score grid
const scoreEl = document.getElementById("score");
const head = document.createElement("div");
head.className = "score-head";
head.innerHTML = `<div>Glas</div>` + DATA.criteria.map(c =>
  `<div>${c.label}<span>${c.hint}</span></div>`).join("");
scoreEl.appendChild(head);

for (const v of DATA.voices) {
  state.scores[v.id] ??= {};
  const row = document.createElement("div");
  row.className = "score-row";
  row.innerHTML = `<div><span class="badge">${v.label}</span></div>`;
  for (const c of DATA.criteria) {
    const seg = document.createElement("div");
    seg.className = "seg";
    seg.setAttribute("role", "radiogroup");
    seg.setAttribute("aria-label", `${c.label} za glas ${v.label}`);
    for (let n = 1; n <= 5; n++) {
      const id = `s-${v.id}-${c.id}-${n}`;
      const checked = state.scores[v.id][c.id] === n ? "checked" : "";
      seg.insertAdjacentHTML("beforeend",
        `<label><input type="radio" name="s-${v.id}-${c.id}" id="${id}" value="${n}" ${checked}>
         <span>${n}</span></label>`);
    }
    seg.addEventListener("change", e => {
      state.scores[v.id][c.id] = Number(e.target.value);
      save(); status(`${c.label} za glas ${v.label}: ${e.target.value}/5`);
    });
    row.appendChild(seg);
  }
  scoreEl.appendChild(row);
}

const notes = document.getElementById("notes");
notes.value = state.notes;
notes.addEventListener("input", () => { state.notes = notes.value; save(); });

function save() { localStorage.setItem(KEY, JSON.stringify(state)); }
function status(msg) { const s = document.getElementById("status"); s.textContent = msg; }

document.getElementById("reveal").addEventListener("click", e => {
  const on = e.currentTarget.getAttribute("aria-pressed") === "true";
  e.currentTarget.setAttribute("aria-pressed", String(!on));
  e.currentTarget.textContent = on ? "Razkrij imena" : "Skrij imena";
  document.querySelectorAll(".real").forEach(el => el.hidden = on);
  document.body.classList.toggle("revealed", !on);
});

document.getElementById("reset").addEventListener("click", () => {
  if (!confirm("Počisti vse ocene in opombe?")) return;
  state = { scores: {}, notes: "" };
  localStorage.removeItem(KEY);
  location.reload();
});

function summary() {
  return {
    generated: new Date().toISOString().slice(0, 10),
    voices: DATA.voices.map(v => ({
      label: v.label,
      engine: v.name,
      scores: state.scores[v.id] || {},
      total: Object.values(state.scores[v.id] || {}).reduce((a, b) => a + b, 0),
    })).sort((a, b) => b.total - a.total),
    notes: state.notes,
  };
}

document.getElementById("export").addEventListener("click", async () => {
  const text = JSON.stringify(summary(), null, 2);
  try { await navigator.clipboard.writeText(text); status("Povzetek kopiran v odložišče."); }
  catch { status("Kopiranje ni uspelo — uporabi »Prenesi JSON«."); }
});

document.getElementById("download").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(summary(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "bakeoff-scores.json";
  a.click();
  URL.revokeObjectURL(a.href);
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
