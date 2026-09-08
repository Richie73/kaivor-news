KAIVOR FP008 — INSTALLATION

Source:
  KAIVOR-LATEST-2026-09-02.zip

Milestone:
  FP008 — Open WebUI Integration Hardening
  Version 0.9.63

IMPORTANT:
  Do NOT overwrite your local config/secrets.py.
  FP008 adds config/secrets.py to .gitignore for future snapshots.

Install:
  Extract the ZIP into:
  /storage/emulated/0/Download/KAIVOR/Kaivor

  Overwrite the existing project files when prompted.

Termux/Ubuntu validation:
  cd /storage/emulated/0/Download/KAIVOR/Kaivor
  python tools/validate_fp008.py

API tests only:
  python tools/run_tests_fp008.py

Start API:
  python kaivor.py api

Open WebUI:
  API Base URL: http://127.0.0.1:8088/v1
  Model: kaivor

Optional API key:
  export KAIVOR_API_KEY='your-strong-local-key'
  Then restart the API and configure the same value in Open WebUI.

After successful validation:
  Create the next project snapshot as:
  /storage/emulated/0/Download/Kaivor-latest.zip
