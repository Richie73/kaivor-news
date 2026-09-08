KAIVOR FP008 CLEANUP

Purpose:
Remove the accidental duplicate nested project directory:

/storage/emulated/0/Download/KAIVOR/Kaivor/Kaivor

The working root project is preserved:

/storage/emulated/0/Download/KAIVOR/Kaivor

This cleanup does NOT touch:
- config/secrets.py
- backups/
- the root project files

Run from the Kaivor project root:

python tools/cleanup_fp008.py

Then validate:

python tools/validate_fp008.py

Then create the clean source-of-truth snapshot:

cd /storage/emulated/0/Download/KAIVOR/Kaivor && rm -f /storage/emulated/0/Download/Kaivor-latest.zip && zip -qr /storage/emulated/0/Download/Kaivor-latest.zip . -x '.git/*' '__pycache__/*' '*/__pycache__/*' '*.pyc' && cp /storage/emulated/0/Download/Kaivor-latest.zip /storage/emulated/0/Download/KAIVOR-LATEST-2026-09-02-FP008-CLEAN.zip
