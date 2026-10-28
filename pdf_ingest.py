#!/usr/bin/env python3
"""PDF ingest for the audiobook pipeline — including photocopies.

Two paths, chosen per page:
  digital  the PDF already has a text layer  → PyMuPDF blocks
  scanned  it is a photocopy                 → Apple Vision OCR (sl-SI, on-device)

Handles the things that actually appear in scanned books: two-page spreads,
running headers/footers, page numbers, hyphenated line breaks, headings, and a
fallback chapter split when the scan has no detectable structure.

Results are cached next to the source hash, so re-rendering never re-OCRs.

    from pdf_ingest import extract_pdf
    title, chapters = extract_pdf("knjiga.pdf", progress=lambda d, t: print(d, t))
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache" / "pdf"
DPI = 300
DIGITAL_MIN_CHARS = 120        # a page with less text than this is treated as a scan
SPREAD_RATIO = 1.15            # width/height above this looks like a two-page scan
CACHE_VERSION = 4              # bump when extraction logic changes


@dataclass
class Page:
    number: int
    blocks: list[tuple[str, str]] = field(default_factory=list)  # (kind, text)
    scanned: bool = False


# ------------------------------------------------------------------ OCR

def _vision_ocr(png: Path) -> list[tuple[str, float, float, float]]:
    """Return (text, x, y, height) lines, top-to-bottom, using Apple Vision."""
    import Quartz
    import Vision
    from Foundation import NSURL

    url = NSURL.fileURLWithPath_(str(png))
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None:
        return []
    cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["sl-SI", "hr-HR", "en-US"])
    req.setUsesLanguageCorrection_(True)
    ok, _ = handler.performRequests_error_([req], None)
    if not ok:
        return []

    lines = []
    for obs in req.results():
        text = obs.topCandidates_(1)[0].string()
        box = obs.boundingBox()
        # origin bottom-left → top-origin y, keep height in pixels later
        lines.append((text, box.origin.x, 1.0 - (box.origin.y + box.size.height), box.size.height))
    lines.sort(key=lambda l: (l[2], l[1]))
    return lines


def _lines_to_blocks(lines: list[tuple[str, float, float, float]], page_width: float) -> list[tuple[str, str]]:
    """Group OCR lines into paragraphs; short oversized lines become headings."""
    if not lines:
        return []
    heights = sorted(h for *_, h in lines)
    median_h = heights[len(heights) // 2]
    lengths = sorted(len(t) for t, *_ in lines)
    median_len = lengths[len(lengths) // 2]

    blocks: list[tuple[str, str]] = []
    current: list[str] = []
    prev_bottom = None

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append(("para", " ".join(current)))
            current = []

    prev_text = ""
    for text, x, top, height in lines:
        text = text.strip()
        if not text:
            continue
        is_heading = height > median_h * 1.22 and len(text) < 90
        gap = 0.0 if prev_bottom is None else top - prev_bottom
        if is_heading:
            flush()
            blocks.append(("heading", text))
            prev_text, prev_bottom = text, top + height
            continue
        # new paragraph on a real gap, or after a short line that ends a sentence
        ends_sentence = prev_text.rstrip().endswith((".", "!", "?", "…", "»", ":"))
        prev_short = 0 < len(prev_text) < median_len * 0.8
        if current and (gap > median_h * 0.75 or (prev_short and ends_sentence)):
            flush()
        current.append(text)
        prev_text, prev_bottom = text, top + height
    flush()
    return blocks


def _ocr_page(pdf_page, spread: bool) -> list[tuple[str, str]]:
    import pymupdf
    from PIL import Image

    pix = pdf_page.get_pixmap(dpi=DPI)
    with tempfile.TemporaryDirectory() as tmp:
        full = Path(tmp) / "page.png"
        pix.save(full)
        if not spread:
            return _lines_to_blocks(_vision_ocr(full), pix.width)

        img = Image.open(full)
        w, h = img.size
        half = w // 2
        blocks: list[tuple[str, str]] = []
        for i, box in enumerate(((0, 0, half, h), (half, 0, w, h))):
            part = Path(tmp) / f"half{i}.png"
            img.crop(box).save(part)
            blocks.extend(_lines_to_blocks(_vision_ocr(part), half))
        return blocks


# ------------------------------------------------------------------ cleaning

def _normalise_running_line(text: str) -> str:
    return re.sub(r"\d+", "#", text.strip().lower())


def _drop_running_lines(pages: list[Page]) -> None:
    """Remove headers/footers: lines repeating on many pages, or bare page numbers."""
    if len(pages) < 4:
        return
    counts: dict[str, int] = {}
    for page in pages:
        for _, text in page.blocks[:1] + page.blocks[-1:]:
            counts[_normalise_running_line(text)] = counts.get(_normalise_running_line(text), 0) + 1
    threshold = max(3, int(len(pages) * 0.3))
    noise = {k for k, v in counts.items() if v >= threshold}

    for page in pages:
        kept = []
        for kind, text in page.blocks:
            norm = _normalise_running_line(text)
            bare_number = bool(re.fullmatch(r"[\s\-–—]*\d{1,4}[\s\-–—]*", text))
            if bare_number or (norm in noise and len(text) < 90):
                continue
            kept.append((kind, text))
        page.blocks = kept


def _join_hyphens(text: str) -> str:
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    return text


def _ocr_fixes(text: str) -> str:
    """Targeted repairs for diacritics Vision commonly drops in scans."""
    text = re.sub(r"\bst\.\s*(?=\d)", "št. ", text)
    text = re.sub(r"\bClan\b", "Član", text)
    text = re.sub(r"\bclan\b", "član", text)
    return text


def _blocks_to_text(blocks: list[tuple[str, str]]) -> list[str]:
    from ocr_fix import restore

    out = []
    for kind, text in blocks:
        text = restore(_ocr_fixes(_join_hyphens(text))).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            out.append(("heading", text) if kind == "heading" else ("para", text))
    return out


# ------------------------------------------------------------------ structure

def _title_from(doc, pages: list[Page], path: Path) -> str:
    meta = ((doc.metadata or {}).get("title") or "").strip()
    # scanners often put the filename in /Title; prefer a real heading then
    if meta and meta.lower() != path.stem.lower() and not meta.lower().endswith(".pdf"):
        return meta
    for page in pages[:3]:
        for kind, text in page.blocks:
            if kind == "heading" and 3 < len(text) < 90:
                return text
    return path.stem


def _chapters(pages: list[Page], toc: list, page_count: int) -> list[tuple[str, list[str]]]:
    """Group page blocks into chapters: TOC first, then headings, then fixed ranges."""
    if toc:
        starts = [(lvl, title, max(1, pno)) for lvl, title, pno in toc if pno and pno <= page_count]
        if starts:
            chapters = []
            for i, (_, title, start) in enumerate(starts):
                end = starts[i + 1][2] if i + 1 < len(starts) else page_count + 1
                blocks = [t for p in pages if start <= p.number < end for _, t in p.blocks]
                if blocks:
                    chapters.append((title.strip(), blocks))
            if chapters:
                return chapters

    chapters: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current: list[str] = []
    for page in pages:
        for kind, text in page.blocks:
            if kind == "heading" and 3 < len(text) < 90:
                if current:
                    chapters.append((current_title or f"Del {len(chapters) + 1}", current))
                current_title, current = text, []
            else:
                current.append(text)
    if current:
        chapters.append((current_title or "Besedilo", current))
    def _split_big(items: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
        """A 500-block "chapter" is unusable in a player; cut it into parts."""
        out: list[tuple[str, list[str]]] = []
        for title, blocks in items:
            if len(blocks) <= 60:
                out.append((title, blocks))
                continue
            parts = [blocks[i:i + 40] for i in range(0, len(blocks), 40)]
            for n, part in enumerate(parts, 1):
                out.append((f"{title} · {n}" if len(parts) > 1 else title, part))
        return out

    chapters = _split_big(chapters)

    if len(chapters) > 1:
        # a running header or a stray line before the first heading should not
        # become its own chapter
        first_title, first_blocks = chapters[0]
        if first_title.startswith("Del ") and len(first_blocks) <= 2:
            # keep real prose, drop a stray running header above the first heading
            kept = [b for b in first_blocks
                    if len(b) > 60 or b.rstrip().endswith((".", "!", "?", "…", ":", "«"))]
            chapters[1] = (chapters[1][0], kept + chapters[1][1])
            chapters = chapters[1:]
        return chapters

    # no structure at all: chunk the pages so the book is still navigable
    chunks: list[tuple[str, list[str]]] = []
    step = 12
    for start in range(0, len(pages), step):
        group = pages[start:start + step]
        text = [t for p in group for _, t in p.blocks]
        if text:
            first, last = group[0].number, group[-1].number
            chunks.append((f"Stran {first}–{last}", text))
    return chunks or [("Besedilo", [t for p in pages for _, t in p.blocks])]


# ------------------------------------------------------------------ entry

def extract_pdf(path: str | Path, progress=None) -> tuple[str, list]:
    """PDF → (title, chapters) where chapters are pipeline.Chapter-compatible."""
    import pymupdf

    source = Path(path)
    stat = source.stat()
    key = hashlib.sha1(
        f"{CACHE_VERSION}|{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode()
    ).hexdigest()
    cache_file = CACHE / f"{key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return data["title"], [_chapter(c) for c in data["chapters"]]

    doc = pymupdf.open(source)
    toc = doc.get_toc(simple=True)
    pages: list[Page] = []
    for i, page in enumerate(doc, 1):
        if progress:
            progress(i - 1, doc.page_count)
        raw = page.get_text("text").strip()
        if len(raw) >= DIGITAL_MIN_CHARS:
            blocks = []
            for b in page.get_text("blocks"):
                text = b[4].strip()
                if text:
                    blocks.append(("para", text))
            pages.append(Page(number=i, blocks=blocks, scanned=False))
        else:
            spread = (page.rect.width / page.rect.height) > SPREAD_RATIO
            pages.append(Page(number=i, blocks=_ocr_page(page, spread), scanned=True))
    if progress:
        progress(doc.page_count, doc.page_count)

    _drop_running_lines(pages)
    for page in pages:
        page.blocks = _blocks_to_text(page.blocks)

    title = _title_from(doc, pages, source)
    chapters = _chapters(pages, toc, doc.page_count)
    doc.close()

    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(
        {"title": title,
         "chapters": [{"title": t, "blocks": b} for t, b in chapters]},
        ensure_ascii=False,
    ))
    return title, [(_chapter({"title": t, "blocks": b})) for t, b in chapters]


def _chapter(data: dict):
    from pipeline import Chapter
    return Chapter(title=data["title"], blocks=data["blocks"])


if __name__ == "__main__":
    import sys
    title, chapters = extract_pdf(sys.argv[1])
    print(f"{title}: {len(chapters)} chapters")
    for c in chapters[:5]:
        print(f"  {c.title} ({len(c.blocks)} blocks)")
        print("   ", c.blocks[0][:120] if c.blocks else "")
