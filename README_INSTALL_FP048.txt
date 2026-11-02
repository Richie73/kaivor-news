KAIVOR FP048 — RESPONSIVE READING EXPERIENCE
============================================

Purpose
-------
Reduce perceived latency by updating the Reading interface locally after successful
mutations instead of reloading the entire dashboard. The server/database remains
the source of truth. Optimistic progress/status updates roll back if the request fails.

Files
-----
Replacement: templates/reading.html
New: tests/test_reading_fp048.py

Install in Termux
-----------------
1. Download Kaivor_FP048_Responsive_Reading.zip to Android Downloads.
2. Run: cd ~/Kaivor && unzip -o ~/storage/shared/Download/Kaivor_FP048_Responsive_Reading.zip -d ~/Kaivor
3. Run: python -m py_compile tests/test_reading_fp048.py
4. Run: python -m pytest -q tests/test_reading_fp048.py tests/test_reading_fp047.py tests/test_reading_web_fp046.py tests/test_reading_web_fp042.py tests/test_reading_postgres_fp043.py tests/test_reading_service.py tests/test_reading_fp041.py tests/test_reading_foundation_fp041.py tests/test_reading_foundation_fp001.py
5. Inspect: git status --short && git diff --check && git diff --stat

Expected behaviour
------------------
- Adding a book inserts the server-confirmed record into the local cache immediately
  after the API response; no dashboard reload is performed.
- Status/progress changes update the affected book locally and roll back on failure.
- Deleting a book removes only that card after server confirmation.
- Notes and lists update local counts/collections after server confirmation.
- Mutating buttons show busy states to prevent repeated submissions.
- Initial dashboard load still fetches the authoritative snapshot.

No database schema changes or secrets are included.
