#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

printf '\n== Kaivor News FP022 validation ==\n'
python -m compileall -q main.py news_feed_quality.py tests
printf '\n[PASS] Python compilation\n'

if ! python -c 'import flask, feedparser, requests' >/dev/null 2>&1; then
  printf '\n[ERROR] Required dependencies are missing. Install them with:\n'
  printf '  python -m pip install -r requirements.txt\n'
  exit 2
fi

python -m pytest -q tests/
printf '\n[PASS] Full tests/ suite\n'

git diff --check
printf '\n[PASS] git diff --check\n'
