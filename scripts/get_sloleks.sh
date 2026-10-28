#!/usr/bin/env bash
# Optional: Sloleks stress table (CC BY-NC-SA 4.0, personal use).
# Downloads 46 MB, unpacks 1.3 GB, builds a 6 MB stress table.
set -euo pipefail
cd "$(dirname "$0")/.."
URL="https://www.clarin.si/repository/xmlui/bitstream/handle/11356/1230/Sloleks2.0.LMF.zip"
mkdir -p .cache/sloleks
[ -f .cache/sloleks/Sloleks2.0.LMF.zip ] || curl -L --fail --progress-bar -o .cache/sloleks/Sloleks2.0.LMF.zip "$URL"
[ -f .cache/sloleks/Sloleks2.0.LMF/sloleks_clarin_2.0.xml ] || unzip -o -q .cache/sloleks/Sloleks2.0.LMF.zip -d .cache/sloleks
.venv-app/bin/python scripts/build_sloleks_stress.py
echo "Stress table ready. In the app tick 'Sloleks naglas', or run:"
echo "  .venv-app/bin/python pipeline.py knjiga.epub -o knjiga.m4b --stress"
