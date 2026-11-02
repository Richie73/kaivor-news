KAIVOR NEWS — FP046 READING INTELLIGENCE

INSTALL (Termux)
1. Extract this ZIP.
2. Copy the included files into the matching paths under ~/Kaivor, overwriting those files.
3. From ~/Kaivor run:
   python -m py_compile reading_web.py reading/repository.py reading/postgres_repository.py tests/test_reading_web_fp046.py
   python -m pytest -q tests/test_reading_web_fp046.py tests/test_reading_web_fp042.py tests/test_reading_postgres_fp043.py tests/test_reading_service.py tests/test_reading_fp041.py tests/test_reading_foundation_fp041.py tests/test_reading_foundation_fp001.py
4. Inspect git diff, then commit and push only after tests pass. Render will deploy from main.

FEATURES
- Edit book details from the book card.
- Confirmed permanent deletion (including related records through existing DB foreign-key cascades).
- Progress history endpoint and mobile-friendly history view.
- Percentage progress automatically moves Want to read -> Reading; 100% -> Finished. Other units do not auto-change status.

NO DATABASE MIGRATION REQUIRED. Existing Supabase tables and records are retained.
