KAIVOR FP047 — READING PERFORMANCE & RELIABILITY
=================================================

Purpose
-------
Fix the asynchronous add-book/add-list form reset error and reduce Reading
dashboard latency by replacing per-book database calls with a bulk snapshot.

Files included
--------------
reading/repository.py
reading/postgres_repository.py
reading_web.py
templates/reading.html
tests/test_reading_fp047.py

No database migration is required. Existing Supabase tables and saved records
are unchanged.

INSTALL — TERMUX
----------------
1. Download Kaivor_FP047_Reading_Performance.zip to Android Downloads.

2. In Termux, run:

   cd ~/Kaivor
   unzip -o ~/storage/shared/Download/Kaivor_FP047_Reading_Performance.zip -d ~/Kaivor

   If Android stores downloads in a different folder, adjust only the ZIP path.
   The archive contains the correct project-relative folder structure.

3. Compile the changed Python files:

   cd ~/Kaivor
   python -m py_compile reading/repository.py reading/postgres_repository.py reading_web.py tests/test_reading_fp047.py

4. Run the focused Reading regression suite:

   python -m pytest -q tests/test_reading_fp047.py tests/test_reading_web_fp046.py tests/test_reading_web_fp042.py tests/test_reading_postgres_fp043.py tests/test_reading_service.py tests/test_reading_fp041.py tests/test_reading_foundation_fp041.py tests/test_reading_foundation_fp001.py

5. Inspect changes before staging:

   git status --short
   git diff --check
   git diff --stat

6. Do not commit or push until the test results and staged file list have
   been reviewed.

WHAT CHANGED
------------
- Capture the add-book and add-list form elements before awaiting network calls.
- Load books, latest progress, note counts, lists and summary through one
  dashboard snapshot operation.
- Use a single PostgreSQL connection for the dashboard snapshot.
- Remove the per-book progress and notes-count connection/query pattern.
- Remove duplicate initial list loading.
- Search and status filtering now operate on the already-loaded book cache,
  rather than issuing a full dashboard request for every keystroke.
- Keep SQLite support and the existing API response fields.
- No credentials, secrets or database connection strings are included.

ROLLBACK
--------
The ZIP only replaces the five files listed above. To roll back, restore those
five files from the pre-install project snapshot. Do not roll back or modify
the Supabase database; FP047 does not change its schema.
