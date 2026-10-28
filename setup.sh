#!/usr/bin/env bash
# One-time setup: venvs, the Slovenian voice, and the app dependencies.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/sl/sl_SI/artur/medium"

echo "== piper =="
[ -d .venv-piper ] || "$PY" -m venv .venv-piper
.venv-piper/bin/pip install -q --upgrade pip
.venv-piper/bin/pip install -q -r requirements-piper.txt

echo "== voice =="
mkdir -p models/piper
for f in sl_SI-artur-medium.onnx sl_SI-artur-medium.onnx.json; do
  [ -f "models/piper/$f" ] || curl -L --fail --progress-bar -o "models/piper/$f" "$VOICE_URL/$f"
done

echo "== app =="
[ -d .venv-app ] || "$PY" -m venv .venv-app
.venv-app/bin/pip install -q --upgrade pip
.venv-app/bin/pip install -q -r requirements-app.txt
if [ "$(uname -s)" = "Darwin" ]; then
  .venv-app/bin/pip install -q -r requirements-macos.txt
else
  echo "! OCR for scanned PDFs uses Apple Vision and is macOS-only."
  echo "  Digital-text PDFs still work; scans would need a Tesseract fallback."
fi

echo
echo "Ready.  Start the app with:"
echo "  .venv-app/bin/python app/server.py    # http://127.0.0.1:8765"
echo "Or from the CLI:"
echo "  .venv-piper/bin/python pipeline.py knjiga.epub -o knjiga.m4b"
