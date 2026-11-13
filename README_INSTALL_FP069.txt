KAIVOR FP069 — SECURE THE LIVE APP
=================================

PURPOSE
-------
FP069 closes the two security gaps found in the 13 Nov 2026 technical
takeover assessment:
1. The mutating API routes (including /api/set_key, which overwrites
   stored provider keys) had no authentication. They now require the
   shared PIN + signed-session gate already used by the Reading
   section: one unlock via the Reading section covers them all.
2. A live-format OpenRouter key sat in 5 stale copies of
   config/local_config.py inside old release/duplicate trees. The key
   value was purged from all five files (verified by pattern only —
   the value was never printed, copied or recorded), the duplicate
   trees were deleted, and the snapshot/gitignore exclusions now cover
   those paths, with a content scan that refuses to ship a snapshot
   containing key material.

IMPORTANT NOTES
---------------
1. Purging the files does NOT revoke the key. Revoke/rotate it at
   OpenRouter (the live app reads its key from environment variables /
   the private store, not from those files, so rotation breaks
   nothing). Until it is revoked, treat it as compromised.
2. The PIN and session secret are YOUR values to set — Muse never
   sets, reads or stores them. See CONFIGURE THE PIN below.
3. The .docx handover §2 snapshot command needs the same exclusions
   added as scripts/kaivor_snapshot.sh (config/local_config.py,
   releases/, Kaivor/, kaivor_fp0172/). The .docx itself was not
   edited; use the script (which now has them) to make snapshots.
4. This milestone does not deploy anything. Install in Termux first
   and run the smoke check below. A Render redeploy is your call,
   afterwards — and remember the Render service needs the same two
   environment variables set in its dashboard (see CONFIGURE THE PIN).
5. Everything deleted in the tidy-up is recoverable from the pre-FP069
   snapshot (the Kaivor-latest.zip from before this install).

CONFIGURE THE PIN
-----------------
The gate needs two environment variables, in every environment that
runs the app (Termux and Render):

  KAIVOR_READING_PIN — your PIN, 8 or more characters.
  KAIVOR_SESSION_SECRET — a long random secret, 32 or more characters.

Termux: add both lines to ~/.bashrc (replace the values with your own),
then start a new Termux session so they take effect:

  export KAIVOR_READING_PIN='your-pin-here'
  export KAIVOR_SESSION_SECRET='a-long-random-secret-here'

Generate a secret with: python3 -c "import secrets; print(secrets.token_hex(24))"

Render: set the same two variables in the service's Environment
settings in the Render dashboard, then redeploy.

Unlock: open the Kaivor News app, tap the 📚 Reading tab, enter the
PIN. That one unlock also unlocks saving keys/sources, saving stories
and the AI features for 12 hours. Until the variables are set, those
actions answer with a clear "locked until configured" message instead
of failing silently.

BACK UP FIRST
-------------
From Termux:

  cd ~/Kaivor
  cp main.py main.py.before-fp069
  cp reading_web.py reading_web.py.before-fp069
  cp templates/index.html templates/index.html.before-fp069
  cp scripts/kaivor_snapshot.sh scripts/kaivor_snapshot.sh.before-fp069
  cp .gitignore .gitignore.before-fp069
  cp tests/test_ai_brief_article_retrieval_fp026.py tests/test_ai_brief_article_retrieval_fp026.py.before-fp069
  cp tests/test_ai_brief_retrieval_quality_fp028.py tests/test_ai_brief_retrieval_quality_fp028.py.before-fp069
  cp tests/test_ai_brief_validation_fp031.py tests/test_ai_brief_validation_fp031.py.before-fp069
  cp tests/test_article_retrieval_diagnostics_fp027.py tests/test_article_retrieval_diagnostics_fp027.py.before-fp069
  cp tests/test_finance_fp0182.py tests/test_finance_fp0182.py.before-fp069

INSTALL (individual files — no ZIP)
---------------------------------
Download the files from chat into Downloads, then from Termux:

  cd ~/Kaivor
  cp ~/storage/downloads/app_security.py ~/Kaivor/app_security.py
  cp ~/storage/downloads/main.py ~/Kaivor/main.py
  cp ~/storage/downloads/reading_web.py ~/Kaivor/reading_web.py
  cp ~/storage/downloads/index.html ~/Kaivor/templates/index.html
  cp ~/storage/downloads/kaivor_snapshot.sh ~/Kaivor/scripts/kaivor_snapshot.sh
  cp ~/storage/downloads/.gitignore ~/Kaivor/.gitignore
  cp ~/storage/downloads/conftest.py ~/Kaivor/tests/conftest.py
  cp ~/storage/downloads/test_news_mutation_auth_fp069.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_snapshot_exclusions_fp069.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_ai_brief_article_retrieval_fp026.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_ai_brief_retrieval_quality_fp028.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_ai_brief_validation_fp031.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_article_retrieval_diagnostics_fp027.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_finance_fp0182.py ~/Kaivor/tests/

If a download picked up a suffix (e.g. main (1).py), rename it to the plain
filename in Downloads before copying.

TIDY-UP (deletions — after the file copies)
-------------------------------------------
Nothing live references these paths (verified by import grep); all are
recoverable from the pre-FP069 snapshot:

  cd ~/Kaivor
  rm -rf Kaivor kaivor_fp0172 releases app
  rm -f run.py test.py update.py
  python3 -c "import os; [os.remove(n) for n in [\"ervice-worker*' -o -iname '*serviceworker*' -o -iname 'manifest.json' -o -iname 'sw.js' ) \", 'ion ===\"', 'sion test ===\"'] if os.path.exists(n)]"

The last line removes the 3 shell-accident filenames at root.

COMPILE
-------
  python -m py_compile app_security.py main.py reading_web.py tests/conftest.py tests/test_news_mutation_auth_fp069.py tests/test_snapshot_exclusions_fp069.py tests/test_ai_brief_article_retrieval_fp026.py tests/test_ai_brief_retrieval_quality_fp028.py tests/test_ai_brief_validation_fp031.py tests/test_article_retrieval_diagnostics_fp027.py tests/test_finance_fp0182.py
  bash -n scripts/kaivor_snapshot.sh

TESTS
-----
  python -m pytest -q tests/test_news_mutation_auth_fp069.py tests/test_snapshot_exclusions_fp069.py tests/test_reading_web_fp042.py tests/test_reading_web_fp046.py tests/test_reading_fp047.py tests/test_reading_postgres_fp043.py tests/test_ai_brief_article_retrieval_fp026.py tests/test_ai_brief_retrieval_quality_fp028.py tests/test_ai_brief_validation_fp031.py tests/test_article_retrieval_diagnostics_fp027.py tests/test_finance_fp0182.py tests/test_news_refresh_fp020.py tests/test_news_reliability_fp022.py

Expected: all pass. Full suite: 434 passed, 11 failed (the same 5
pre-existing environment-only failures as the baseline — 2 MCP httpx,
3 NewsData needing the device's real config/secrets.py — plus 6
test_credential_migration_fp037 setup failures that are a local stub
artifact), 2 skipped.

SMOKE CHECK (LIVE)
------------------
1. Restart the app if it is running under gunicorn.
2. Without unlocking, try saving a key in Settings: you should get a
   clear locked message (503 if the PIN/secret are not configured,
   401 if they are but the session is not unlocked).
3. Unlock via the 📚 Reading tab with the PIN, then save a key: it
   should save normally.
4. Check a GET route still works open (e.g. open /api/health in the
   browser — it should return success without unlocking).
5. Run the snapshot script and confirm it prints PASS with no key
   material detected:
     bash scripts/kaivor_snapshot.sh

ROLLBACK
--------
  cd ~/Kaivor
  mv main.py.before-fp069 main.py
  mv reading_web.py.before-fp069 reading_web.py
  mv templates/index.html.before-fp069 templates/index.html
  mv scripts/kaivor_snapshot.sh.before-fp069 scripts/kaivor_snapshot.sh
  mv .gitignore.before-fp069 .gitignore
  mv tests/test_ai_brief_article_retrieval_fp026.py.before-fp069 tests/test_ai_brief_article_retrieval_fp026.py
  mv tests/test_ai_brief_retrieval_quality_fp028.py.before-fp069 tests/test_ai_brief_retrieval_quality_fp028.py
  mv tests/test_ai_brief_validation_fp031.py.before-fp069 tests/test_ai_brief_validation_fp031.py
  mv tests/test_article_retrieval_diagnostics_fp027.py.before-fp069 tests/test_article_retrieval_diagnostics_fp027.py
  mv tests/test_finance_fp0182.py.before-fp069 tests/test_finance_fp0182.py
  rm app_security.py tests/conftest.py tests/test_news_mutation_auth_fp069.py tests/test_snapshot_exclusions_fp069.py

Then restart the app. (The tidy-up deletions are not rolled back by
this: restore them from the pre-FP069 snapshot if ever needed.)
