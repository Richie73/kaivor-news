#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/Kaivor"
out="$HOME/storage/shared/Kaivor Snapshots/Kaivor-latest.zip"
mkdir -p "$(dirname "$out")"
rm -f "$out"
zip -r "$out" . \
  -x '.git/*' '*/.git/*' \
     '__pycache__/*' '*/__pycache__/*' \
     '.pytest_cache/*' '*/.pytest_cache/*' \
     '.venv/*' '*/.venv/*' 'venv/*' '*/venv/*' \
     'safety-backups/*' 'backups/*' \
     '.env' '*/.env' \
     'config/news_secrets.json' 'config/*secrets*.json' \
     'config/local_config.py' '*/config/local_config.py' \
     'releases' 'releases/*' '*/releases' '*/releases/*' \
     'Kaivor' 'Kaivor/*' '*/Kaivor' '*/Kaivor/*' \
     'kaivor_fp0172' 'kaivor_fp0172/*' '*/kaivor_fp0172' '*/kaivor_fp0172/*' \
     '*.pyc' 'reports/kaimprove/*'
echo "Checking archive for sensitive files..."
if unzip -Z1 "$out" | grep -Ei '(^|/)(news_secrets\.json|\.env)$|(^|/)secrets[^/]*\.json$|(^|/)local_config\.py$|(^|/)(releases|Kaivor|kaivor_fp0172)(/|$)'; then
  rm -f "$out"
  echo 'ERROR: sensitive file detected; unsafe archive removed.' >&2
  exit 1
fi
echo "Checking archive contents for leaked API keys..."
tmpdir="$(mktemp -d)"
unzip -q "$out" -d "$tmpdir"
key_found=0
# OpenRouter keys (real keys carry 64 characters after the prefix) and
# OpenAI project keys. tests/ is excluded from both scans: it holds
# deliberate fake fixtures (e.g. test_kaimprove_fp035.py), which are
# token-shaped by design and would otherwise trip the scan.
if grep -rEq --exclude-dir=tests 'sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9]{20,}' "$tmpdir"; then
  key_found=1
fi
# Bare sk- keys, excluding tests/ which holds deliberate fake fixtures.
if grep -rEq --exclude-dir=tests 'sk-[A-Za-z0-9]{20,}' "$tmpdir"; then
  key_found=1
fi
rm -rf "$tmpdir"
if [ "$key_found" -eq 1 ]; then
  rm -f "$out"
  echo 'ERROR: possible API key material in archive contents; unsafe archive removed.' >&2
  exit 1
fi
echo "PASS: clean snapshot created at: $out"
