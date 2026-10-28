#!/usr/bin/env python3
"""EPUB → Slovenian audiobook (M4B), local only.

    python3 pipeline.py examples/vzorec.epub -o vzorec.m4b

Stages: EPUB → chapters → blocks → sentences → norm_sl → Piper → loudness →
chaptered M4B. Every stage is inspectable; audio is cached per sentence so a
re-render after a text fix only redoes what changed.

Stdlib only (plus ffmpeg and the piper venv). No network, no account.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from norm_sl import normalize  # noqa: E402
from pron_sl import pronounce  # noqa: E402

PIPER = ROOT / ".venv-piper" / "bin" / "piper"
MODEL = ROOT / "models" / "piper" / "sl_SI-artur-medium.onnx"
CACHE = ROOT / ".cache" / "tts"
WORK = ROOT / ".cache" / "work"

BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "blockquote", "li", "div", "td"}
SKIP_TAGS = {"script", "style", "nav", "svg", "img", "head", "title", "meta", "link"}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[»„\"'(]?\S)")
MAX_CHUNK = 380

# eSpeak reads plain numbers with correct Slovenian stress; spelled-out numerals
# get its default stress and sound wrong. So the default is minimal rewriting:
# fix money, dates, ordinals, symbols and abbreviations, leave digits alone.
MINIMAL_NORMALIZATION = True

# Warmth + glue + a small room. Measured effect: spectral centroid 1.15 → 1.07 kHz,
# pitch movement unchanged (5.2–5.7 semitones either way).
STUDIO_CHAIN = (
    "highpass=f=70,"
    "equalizer=f=190:t=q:w=1.0:g=2.5,"
    "equalizer=f=3300:t=q:w=1.4:g=-2.5,"
    "equalizer=f=6800:t=q:w=2.0:g=-1.5,"
    "acompressor=threshold=-20dB:ratio=2.2:attack=8:release=180:makeup=3,"
    "aecho=0.9:0.55:23|41|67:0.05|0.035|0.02"
)


def speed_for(sentence: str) -> float:
    """Long narration slows, short dialogue snaps. Bounded to ±7 %."""
    n = len(sentence)
    if n > 170:
        return 1.07
    if n > 110:
        return 1.04
    if n < 55:
        return 0.98
    return 1.01


def pause_for(sentence: str, paragraph_end: bool) -> float:
    if paragraph_end:
        return 0.85
    stripped = sentence.rstrip("«»\"' ")
    if stripped.endswith(("?", "!")):
        return 0.55
    if stripped.endswith("…"):
        return 0.7
    return 0.45


# ------------------------------------------------------------------ EPUB

class _Blocks(html.parser.HTMLParser):
    """Collect text per block element, ignoring scripts and nav."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] = []
        self._skip = 0
        self.headings: list[str] = []
        self._heading: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag in {"h1", "h2", "h3"}:
            self._flush()
            self._heading = []
        elif tag in BLOCK_TAGS and self._buf:
            self._flush()

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in {"h1", "h2", "h3"} and self._heading is not None:
            text = " ".join("".join(self._heading).split())
            if text:
                self.headings.append(text)
            self._heading = None
            self._flush()
        elif tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        self._buf.append(data)
        if self._heading is not None:
            self._heading.append(data)

    def _flush(self):
        text = " ".join("".join(self._buf).split())
        if text:
            self.blocks.append(text)
        self._buf = []

    def close(self):
        super().close()
        self._flush()


@dataclass
class Chapter:
    title: str
    blocks: list[str] = field(default_factory=list)


def read_epub(path: Path) -> tuple[str, list[Chapter]]:
    with zipfile.ZipFile(path) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        opf_path = container.find(".//{*}rootfile").get("full-path")
        opf = ET.fromstring(z.read(opf_path))
        base = str(Path(opf_path).parent)
        ns = opf.tag.split("}")[0][1:] if opf.tag.startswith("{") else ""
        q = (lambda tag: f"{{{ns}}}{tag}") if ns else (lambda tag: tag)

        manifest = {}
        for item in opf.iter(q("item")):
            manifest[item.get("id")] = (item.get("href"), item.get("properties", ""))

        dc = "{http://purl.org/dc/elements/1.1/}"
        title_el = opf.find(f".//{dc}title")
        book_title = title_el.text.strip() if title_el is not None and title_el.text else path.stem

        chapters: list[Chapter] = []
        for ref in opf.iter(q("itemref")):
            href, props = manifest.get(ref.get("idref"), (None, ""))
            if not href or "nav" in props:
                continue
            name = str(Path(base) / href) if base != "." else href
            if name not in z.namelist():
                continue
            parser = _Blocks()
            parser.feed(z.read(name).decode("utf-8", "replace"))
            parser.close()
            if not parser.blocks:
                continue
            title = parser.headings[0] if parser.headings else f"Poglavje {len(chapters) + 1}"
            chapters.append(Chapter(title=title, blocks=parser.blocks))
        return book_title, chapters


# ------------------------------------------------------------------ text

def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_SPLIT.split(text) if p.strip()]
    # Piper writes an empty WAV (and crashes) when the input has no words
    parts = [p for p in parts if re.search(r"\w", p)]
    out: list[str] = []
    for part in parts:
        while len(part) > MAX_CHUNK:
            cut = max(part.rfind("; ", 0, MAX_CHUNK), part.rfind(", ", 0, MAX_CHUNK))
            cut = cut + 1 if cut > 80 else MAX_CHUNK
            out.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            out.append(part)
    return out


# ------------------------------------------------------------------ audio

def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def silence(seconds: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
              f"anullsrc=r=22050:cl=mono", "-t", f"{seconds}", "-c:a", "pcm_s16le", str(out)])
    return out


def say(text: str, speed: float = 1.0) -> Path | None:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text).strip()
    if not re.search(r"\w", text):
        return None
    key = hashlib.sha1(f"{MODEL.name}|{speed:.3f}|{text}".encode()).hexdigest()
    out = CACHE / key[:2] / f"{key}.wav"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run([str(PIPER), "-m", str(MODEL), "-c", f"{MODEL}.json", "-f", str(out),
              "--length-scale", f"{speed:.3f}", "--noise-scale", "0.70",
              "--noise-w-scale", "1.05", "--sentence-silence", "0.2"], input=text.encode())
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="replace").strip().splitlines()
        detail = stderr[-1] if stderr else "brez sporočila"
        raise RuntimeError(f"Piper ni mogel sintetizirati {text[:80]!r}: {detail}") from exc
    if not out.exists():
        raise RuntimeError(f"Piper ni ustvaril datoteke za {text[:80]!r}")
    return out


def concat(parts: list[Path], out: Path) -> Path:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
          "-i", str(listing), "-c", "copy", str(out)])
    return out


def duration(path: Path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(path)]).stdout.decode().strip()
    return float(out)


def render_blocks(blocks: list[str], name: str, *, minimal: bool | None = None,
                  use_names: bool = True, pace: bool = True) -> Path:
    """Blocks of one chapter → one wav, with normalisation and pronunciation."""
    if minimal is None:
        minimal = MINIMAL_NORMALIZATION
    WORK.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for block in blocks:
        spoken, warnings = normalize(block, minimal=minimal)
        for w in warnings:
            print(f"  ! {w}", file=sys.stderr)
        if use_names:
            spoken, changes = pronounce(spoken)
            for src, dst in changes:
                print(f"  ~ {src} → {dst}", file=sys.stderr)
        sentences = split_sentences(spoken)
        for i, sentence in enumerate(sentences):
            wav = say(sentence, speed_for(sentence) if pace else 1.0)
            if wav is not None:
                parts.append(wav)
            if pace:
                pause = pause_for(sentence, paragraph_end=i == len(sentences) - 1)
            else:
                pause = 0.35
            parts.append(silence(pause, WORK / f"gap_{pause}.wav"))
    parts.append(silence(0.9, WORK / "tail.wav"))
    out = WORK / f"{name}.wav"
    concat(parts, out)
    return out


def build_chapter(chapter: Chapter, index: int) -> Path:
    return render_blocks(chapter.blocks, f"ch{index:02d}")


def studio(src: Path, dst: Path) -> Path:
    """Warmth + glue + small room, then loudness to the audiobook target."""
    staged = dst.with_suffix(".stage.wav")
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", STUDIO_CHAIN,
          "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(staged)])
    loudnorm(staged, dst)
    return dst


def loudnorm(src: Path, dst: Path) -> None:
    probe = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                  "loudnorm=I=-19:TP=-3:LRA=11:print_format=json", "-f", "null", "-"])
    import json
    text = probe.stderr.decode()
    m = json.loads(text[text.rfind("{"): text.rfind("}") + 1])
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
          f"loudnorm=I=-19:TP=-3:LRA=11:measured_I={m['input_i']}"
          f":measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
          "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)])


def write_m4b(book_title: str, chapters: list[tuple[str, float]], audio: Path, out: Path) -> None:
    meta = out.with_suffix(".ffmeta")
    lines = [";FFMETADATA1", f"title={book_title}", "album=" + book_title,
             "artist=Pipeline", "genre=Audiobook"]
    t = 0.0
    for title, length in chapters:
        start_ms, end_ms = int(t * 1000), int((t + length) * 1000)
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={start_ms}",
                  f"END={end_ms}", f"title={title}"]
        t += length
    meta.write_text("\n".join(lines) + "\n")
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-i", str(meta),
          "-map_metadata", "1", "-map", "0:a", "-c:a", "aac", "-b:a", "64k",
          "-movflags", "+faststart", str(out)])


# ------------------------------------------------------------------ main

def read_book(path: Path | str, progress=None):
    """EPUB or PDF (digital text layer, or OCR for photocopies)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from pdf_ingest import extract_pdf
        return extract_pdf(path, progress=progress)
    return read_epub(path)


def render_book(epub: Path, out: Path, *, minimal: bool = True, names: bool = True,
                pace: bool = True, studio_chain: bool = True, limit: int = 0,
                progress=None) -> dict:
    """Render a whole EPUB. progress(done, total, chapter_title) is called per chapter."""
    book_title, chapters = read_book(epub)
    if limit:
        chapters = chapters[:limit]
    total = len(chapters)

    chapter_files, chapter_meta = [], []
    for i, chapter in enumerate(chapters, 1):
        if progress:
            progress(i - 1, total, chapter.title)
        path = render_blocks(chapter.blocks, f"ch{i:02d}", minimal=minimal,
                             use_names=names, pace=pace)
        chapter_files.append(path)
        chapter_meta.append((chapter.title, duration(path)))

    gap = silence(1.2 if pace else 0.35, WORK / "chapter_gap.wav")
    parts: list[Path] = []
    for path in chapter_files:
        parts += [path, gap]
    joined = WORK / "book_raw.wav"
    concat(parts, joined)

    normalized = WORK / "book_norm.wav"
    if studio_chain:
        studio(joined, normalized)
    else:
        loudnorm(joined, normalized)
    write_m4b(book_title, chapter_meta, normalized, out)
    if progress:
        progress(total, total, "končano")

    return {
        "title": book_title,
        "chapters": [{"title": t, "duration": round(d, 2)} for t, d in chapter_meta],
        "duration": round(duration(normalized), 2),
        "path": str(out),
        "size": out.stat().st_size,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="EPUB → slovenska zvočna knjiga (M4B)")
    ap.add_argument("epub")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--limit", type=int, default=0, help="only the first N chapters")
    ap.add_argument("--plain", action="store_true", help="no pacing, no studio chain")
    ap.add_argument("--full-text", action="store_true",
                    help="spell out numbers too (worse stress, use for testing)")
    ap.add_argument("--no-names", action="store_true", help="skip the pronunciation lexicon")
    args = ap.parse_args()

    global MINIMAL_NORMALIZATION
    if args.full_text:
        MINIMAL_NORMALIZATION = False

    src = Path(args.epub)
    out = Path(args.out) if args.out else src.with_suffix(".m4b")

    def progress(done: int, total: int, title: str) -> None:
        if done < total:
            print(f"[{done + 1}/{total}] {title}", flush=True)

    result = render_book(
        src, out,
        minimal=MINIMAL_NORMALIZATION,
        names=not args.no_names,
        pace=not args.plain,
        studio_chain=not args.plain,
        limit=args.limit,
        progress=progress,
    )
    print(f"\n{out} — {result['duration'] / 60:.1f} min, {len(result['chapters'])} chapters, "
          f"{result['size'] / 1e6:.1f} MB")
    print("cache:", sum(1 for _ in CACHE.rglob("*.wav")), "sentences")


if __name__ == "__main__":
    main()
