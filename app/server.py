#!/usr/bin/env python3
"""Local web app for the Slovenian ebook → audiobook pipeline.

    .venv-app/bin/python app/server.py      # http://127.0.0.1:8765

One user, one machine, no accounts. Books and outputs live under app/library;
the SQLite file is the library index. Rendering runs in a single background
worker so the UI stays responsive and the CPU is not oversubscribed.
"""

from __future__ import annotations

import json
import queue
from contextlib import contextmanager
import sqlite3
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pipeline  # noqa: E402

APP_DIR = Path(__file__).resolve().parent
LIBRARY = APP_DIR / "library"
DB_PATH = APP_DIR / "library.db"
STATIC = APP_DIR / "static"

LIBRARY.mkdir(exist_ok=True)
app = FastAPI(title="ebook-audio", docs_url=None, redoc_url=None)
jobs: "queue.Queue[str]" = queue.Queue()
_lock = threading.Lock()


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, path TEXT NOT NULL,
              created TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
              output TEXT, duration REAL, chapters TEXT, error TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, book_id TEXT NOT NULL, status TEXT NOT NULL,
              done INTEGER DEFAULT 0, total INTEGER DEFAULT 0, message TEXT,
              settings TEXT, created TEXT NOT NULL, finished TEXT, error TEXT
            );
            """
        )
        # a restart leaves queued/running rows behind; mark them failed
        conn.execute("UPDATE jobs SET status='error', error='prekinjeno ob ponovnem zagonu' "
                     "WHERE status IN ('queued','running')")
        conn.execute("UPDATE books SET status='ready' WHERE status IN ('queued','rendering')")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_book(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"], "title": r["title"], "status": r["status"],
        "duration": r["duration"], "error": r["error"],
        "chapters": json.loads(r["chapters"]) if r["chapters"] else [],
        "has_audio": bool(r["output"]),
    }


class ImportPath(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class RenderSettings(BaseModel):
    mode: str = Field(default="minimal", pattern="^(minimal|full)$")
    names: bool = True
    pace: bool = False
    studio: bool = False
    stress: bool = True


@app.get("/api/books")
def list_books():
    with db() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY created DESC").fetchall()
    return [row_book(r) for r in rows]


@app.post("/api/books/path", status_code=201)
def add_by_path(payload: ImportPath):
    path = Path(payload.path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in (".epub", ".pdf"):
        raise HTTPException(400, "Pot mora kazati na .epub ali .pdf datoteko.")
    _check_book_file(path)
    return _insert_book(path)


@app.post("/api/books/upload", status_code=201)
async def upload_book(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    if not name.endswith((".epub", ".pdf")):
        raise HTTPException(400, "Naloži .epub ali .pdf datoteko.")
    suffix = ".pdf" if name.endswith(".pdf") else ".epub"
    target = LIBRARY / f"{uuid.uuid4().hex}{suffix}"
    data = await file.read()
    if len(data) > 250 * 1024 * 1024:
        raise HTTPException(413, "Datoteka je večja od 250 MB.")
    target.write_bytes(data)
    try:
        _check_book_file(target)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    return _insert_book(target)


def _check_book_file(path: Path) -> None:
    """Validate EPUB container or PDF header without doing the expensive work."""
    if path.suffix.lower() == ".pdf":
        try:
            import pymupdf
            with pymupdf.open(path) as doc:
                if doc.page_count < 1:
                    raise HTTPException(400, "PDF je brez strani.")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "Datoteka ni veljaven PDF.")
        return
    try:
        with zipfile.ZipFile(path) as z:
            if "META-INF/container.xml" not in z.namelist():
                raise HTTPException(400, "Datoteka ni veljaven EPUB.")
    except zipfile.BadZipFile:
        raise HTTPException(400, "Datoteka ni veljaven EPUB.")


def _insert_book(path: Path) -> dict:
    """EPUB: extract now (fast). PDF: queue extraction (OCR can take minutes)."""
    book_id = uuid.uuid4().hex
    if path.suffix.lower() == ".pdf":
        title = path.stem
        with _lock, db() as conn:
            conn.execute(
                "INSERT INTO books (id,title,path,created,status,chapters) VALUES (?,?,?,?,?,?)",
                (book_id, title, str(path), now(), "extracting", "[]"),
            )
            job_id = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO jobs (id,book_id,status,message,settings,created) VALUES (?,?,?,?,?,?)",
                (job_id, book_id, "queued", "berem PDF", json.dumps({"kind": "extract"}), now()),
            )
            row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        jobs.put(job_id)
        return row_book(row)

    try:
        title, chapters = pipeline.read_epub(path)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        raise HTTPException(400, f"EPUB se ne da prebrati: {exc}")
    with db() as conn:
        conn.execute(
            "INSERT INTO books (id,title,path,created,status,chapters) VALUES (?,?,?,?,?,?)",
            (book_id, title, str(path), now(), "ready",
             json.dumps([{"title": c.title, "blocks": len(c.blocks)} for c in chapters])),
        )
        row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    return row_book(row)


@app.get("/api/books/{book_id}")
def get_book(book_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Knjiga ne obstaja.")
    return row_book(row)


@app.post("/api/books/{book_id}/render", status_code=202)
def render(book_id: str, settings: RenderSettings):
    with _lock, db() as conn:
        book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book:
            raise HTTPException(404, "Knjiga ne obstaja.")
        active = conn.execute(
            "SELECT id FROM jobs WHERE book_id=? AND status IN ('queued','running')",
            (book_id,),
        ).fetchone()
        if active:
            raise HTTPException(409, "Za to knjigo že teče izdelava.")
        if book["status"] == "extracting":
            raise HTTPException(409, "Besedilo se še pripravlja (OCR).")
        job_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO jobs (id,book_id,status,message,settings,created) VALUES (?,?,?,?,?,?)",
            (job_id, book_id, "queued", "v čakalni vrsti",
             json.dumps(settings.model_dump()), now()),
        )
        conn.execute("UPDATE books SET status='queued', error=NULL WHERE id=?", (book_id,))
    jobs.put(job_id)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Opravilo ne obstaja.")
    return dict(row)


@app.get("/api/books/{book_id}/audio")
def audio(book_id: str):
    with db() as conn:
        row = conn.execute("SELECT output FROM books WHERE id=?", (book_id,)).fetchone()
    if not row or not row["output"]:
        raise HTTPException(404, "Zvok še ni izdelan.")
    path = Path(row["output"])
    if not path.is_file():
        raise HTTPException(410, "Datoteka je bila premaknjena ali izbrisana.")
    return FileResponse(path, media_type="audio/mp4", filename=f"{path.stem}.m4b")


@app.delete("/api/books/{book_id}", status_code=204)
def delete_book(book_id: str):
    with db() as conn:
        conn.execute("DELETE FROM jobs WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    from fastapi import Response
    return Response(status_code=204)


def worker() -> None:
    while True:
        job_id = jobs.get()
        try:
            _run_job(job_id)
        except Exception as exc:  # noqa: BLE001 - recorded for the UI
            with db() as conn:
                conn.execute(
                    "UPDATE jobs SET status='error', error=?, finished=? WHERE id=?",
                    (str(exc), now(), job_id),
                )
                conn.execute(
                    "UPDATE books SET status='error', error=? WHERE id="
                    "(SELECT book_id FROM jobs WHERE id=?)", (str(exc), job_id))
        finally:
            jobs.task_done()


def _run_job(job_id: str) -> None:
    with db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        book = conn.execute("SELECT * FROM books WHERE id=?", (job["book_id"],)).fetchone()
    settings = json.loads(job["settings"] or "{}")
    if settings.get("kind") == "extract":
        _run_extract(job_id, book)
        return
    out = LIBRARY / f"{book['id']}.m4b"
    with db() as conn:
        conn.execute("UPDATE jobs SET status='running', message='zbiram poglavja' WHERE id=?",
                     (job_id,))
        conn.execute("UPDATE books SET status='rendering' WHERE id=?", (book["id"],))

    def progress(done: int, total: int, title: str) -> None:
        with db() as conn:
            conn.execute(
                "UPDATE jobs SET done=?, total=?, message=? WHERE id=?",
                (done, total, title, job_id),
            )

    pipeline.STRESS_MODE = bool(settings.get("stress", True))
    result = pipeline.render_book(
        Path(book["path"]), out,
        minimal=settings.get("mode", "minimal") == "minimal",
        names=settings.get("names", True),
        pace=settings.get("pace", False),
        studio_chain=settings.get("studio", False),
        progress=progress,
    )
    with db() as conn:
        conn.execute(
            "UPDATE jobs SET status='done', done=total, message='končano', finished=? WHERE id=?",
            (now(), job_id),
        )
        conn.execute(
            "UPDATE books SET status='done', output=?, duration=?, chapters=?, error=NULL "
            "WHERE id=?",
            (str(out), result["duration"],
             json.dumps(result["chapters"], ensure_ascii=False), book["id"]),
        )


def _run_extract(job_id: str, book: sqlite3.Row) -> None:
    path = Path(book["path"])

    def progress(done: int, total: int, page: str = "") -> None:
        with db() as conn:
            conn.execute("UPDATE jobs SET done=?, total=?, message=? WHERE id=?",
                         (done, total, "berem PDF", job_id))

    title, chapters = pipeline.read_book(path, progress=progress)
    with db() as conn:
        conn.execute(
            "UPDATE books SET title=?, status='ready', chapters=?, error=NULL WHERE id=?",
            (title, json.dumps([{"title": c.title, "blocks": len(c.blocks)}
                                for c in chapters], ensure_ascii=False), book["id"]),
        )
        conn.execute(
            "UPDATE jobs SET status='done', message='besedilo pripravljeno', finished=? WHERE id=?",
            (now(), job_id),
        )


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


init_db()
threading.Thread(target=worker, daemon=True).start()
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
