KAIVOR FP068 — FREEDIUM INTEGRATION AND FREEDIUM PUBLISHERS' NEWS FEEDS
=====================================================================

PURPOSE
-------
FP068 connects Kaivor News to Freedium in three slices:
1. When direct article extraction fails on a paywalled article from Medium,
   the New York Times, the Washington Post, Bloomberg, Reuters, The
   Economist or the Financial Times, the extractor retries once through the
   Freedium Mirror (https://freedium-mirror.cfd). A failed mirror attempt
   returns the original result, so a mirror outage costs nothing.
2. The news UI shows an "Unlock via Freedium" link for supported articles.
   The NYT subscription link stays primary.
3. 13 feeds from those publishers join the matching news categories
   (World +3, Technology +3, Business +4, Science +2, UK +1). Reuters and
   Medium have no registry feed: Reuters has no working public RSS feed,
   and Medium has no editorial feed. Both still get the extractor fallback
   when their links arrive via other sources.

IMPORTANT NOTES
---------------
1. The Freedium Mirror is a third-party beta service. It goes up and down
   and does not unlock everything. FP068 treats it strictly as a fallback.
2. Kaivor never sends credentials, cookies or payment details to the
   mirror — only the article URL.
3. No secrets are in this bundle. config/secrets.py is untouched.
4. This milestone does not deploy anything. Install in Termux first and
   run the smoke check below. A Render redeploy is your call, afterwards.
5. The three Washington Post feeds could not be live-fetched from Muse's
   environment (feeds.washingtonpost.com was unreachable there). The smoke
   check below confirms them from Termux. If any new feed reports an error
   there, remove that one feed from DEFAULT_FEEDS in news_freshness.py
   rather than shipping a dead feed.

BACK UP FIRST
-------------
From Termux:

  cd ~/Kaivor
  cp article_extractor.py article_extractor.py.before-fp068
  cp publisher_access.py publisher_access.py.before-fp068
  cp news_freshness.py news_freshness.py.before-fp068
  cp main.py main.py.before-fp068
  cp templates/index.html templates/index.html.before-fp068

INSTALL (individual files — no ZIP)
---------------------------------
Download the 8 files from chat into Downloads, then from Termux:

  cd ~/Kaivor
  cp ~/storage/downloads/article_extractor.py ~/Kaivor/article_extractor.py
  cp ~/storage/downloads/publisher_access.py ~/Kaivor/publisher_access.py
  cp ~/storage/downloads/news_freshness.py ~/Kaivor/news_freshness.py
  cp ~/storage/downloads/main.py ~/Kaivor/main.py
  cp ~/storage/downloads/index.html ~/Kaivor/templates/index.html
  cp ~/storage/downloads/test_freedium_fallback_fp068.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_freedium_access_fp068.py ~/Kaivor/tests/
  cp ~/storage/downloads/test_freedium_feeds_fp068.py ~/Kaivor/tests/

If a download picked up a suffix (e.g. main (1).py), rename it to the plain
filename in Downloads before copying. (An archive ZIP of the same files
exists in the handover folder, but Richie prefers individual files.)

COMPILE
-------
  python -m py_compile article_extractor.py publisher_access.py news_freshness.py main.py tests/test_freedium_fallback_fp068.py tests/test_freedium_access_fp068.py tests/test_freedium_feeds_fp068.py

TESTS
-----
  python -m pytest -q tests/test_freedium_fallback_fp068.py tests/test_freedium_access_fp068.py tests/test_freedium_feeds_fp068.py tests/test_article_extractor_fp026.py tests/test_publisher_access_fp023.py tests/test_publisher_feeds_fp024.py tests/test_news_freshness.py tests/test_ai_brief_article_retrieval_fp026.py tests/test_ai_brief_retrieval_quality_fp028.py tests/test_article_retrieval_diagnostics_fp027.py

Expected: all pass. (The full suite has 5 pre-existing environment-only
failures unrelated to FP068: 2 MCP httpx tests and 3 NewsData tests that
need the device's real config/secrets.py.)

SMOKE CHECK (LIVE)
------------------
1. Restart the app if it is running under gunicorn, then refresh news.
2. Check /api/news-quality: each new feed should report ok with articles.
   Pay particular attention to the three Washington Post feeds (see note 5
   above) and the NYT Science feed.
3. Open an article from a paywalled publisher (e.g. a Medium or FT story)
   and request an AI Brief. When the mirror unlocks it, the brief's
   retrieval record shows content_source "freedium_mirror".
4. Check a Medium or Bloomberg article card shows the "Unlock via
   Freedium" link, and that an NYT card shows both the subscription link
   and the Freedium link.

ROLLBACK
--------
  cd ~/Kaivor
  mv article_extractor.py.before-fp068 article_extractor.py
  mv publisher_access.py.before-fp068 publisher_access.py
  mv news_freshness.py.before-fp068 news_freshness.py
  mv main.py.before-fp068 main.py
  mv templates/index.html.before-fp068 templates/index.html
  rm tests/test_freedium_fallback_fp068.py tests/test_freedium_access_fp068.py tests/test_freedium_feeds_fp068.py

Then restart the app.
