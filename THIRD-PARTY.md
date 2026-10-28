# Third-party components

This project is a thin layer over other people's work. If you redistribute it,
these obligations travel with it.

| Component | License | Notes |
|---|---|---|
| **PyMuPDF** (`pymupdf`) | **AGPL-3.0** or commercial | PDF text extraction and page rendering. This is why the project itself is AGPL-3.0. |
| **piper-tts** + **espeak-ng** | MIT (Piper), **GPL-3.0** (eSpeak) | The Piper wheel bundles eSpeak data. |
| **Piper voice `sl_SI-artur-medium`** | model card: CC-BY-4.0 dataset | Trained on the ARTUR studio corpus (speaker G0911). Attribution required. |
| **ARTUR corpus** | CC-BY-3.0 | Verdonik et al., CLARIN.SI, handle 11356/1776. |
| **wordfreq** | MIT / Apache-2.0 (data) | Used to restore Slovenian diacritics lost by OCR. |
| **FastAPI / Starlette / Uvicorn** | MIT / BSD | Local web app. |
| **Apple Vision** | system framework | On-device OCR, macOS only. |
| **Slovenian pronunciation lexicon** | this project | Hand-curated respellings; verify before relying on it. |

The audiobooks you make are your responsibility: converting a book you own for
private listening is one thing, distributing the result is another.
