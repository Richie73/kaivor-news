KAIVOR FP017.1 — MULTI-SOURCE FRESH NEWS & FEED QUALITY
========================================================

SOURCE OF TRUTH
---------------
This bundle is rebuilt directly from the FP017 Personal Relevance snapshot.
It restores the complete FP017 codebase and adds FP017.1 on top.

WHAT CHANGED
------------
- 25 curated RSS feeds across World, Technology, Business, Science, UK and Sport.
- Parallel feed retrieval so slow feeds do not block the whole refresh.
- Up to 15 recent items per feed.
- 72-hour default freshness window.
- Timestamp-aware filtering and newest-first ordering.
- Future-dated/broken feed items rejected.
- Custom RSS sources retained.
- Feed tier/source metadata retained through normalisation.
- Existing Guardian API, puzzles, evidence, timeline, importance and personal relevance layers retained.

INSTALL
-------
From Termux:

cd ~/Kaivor && unzip -o ~/storage/downloads/Kaivor-FP017.1-Multi-Source-Fresh-News-CORRECTED.zip

Then compile:

cd ~/Kaivor && python -m py_compile main.py news_store.py news_freshness.py

FP017.1 test:

cd ~/Kaivor && PYTHONPATH=. python tests/test_news_freshness.py

Existing FP017 tests:

cd ~/Kaivor && PYTHONPATH=. python tests/test_story_intelligence.py && PYTHONPATH=. python tests/test_intelligence_quality.py && PYTHONPATH=. python tests/test_evidence_engine.py && PYTHONPATH=. python tests/test_evidence_clarity.py && PYTHONPATH=. python tests/test_story_timeline.py && PYTHONPATH=. python tests/test_importance_engine.py && PYTHONPATH=. python tests/test_personal_relevance.py

CONFIGURATION
-------------
Default freshness: 72 hours.
Override with:
  KAIVOR_NEWS_MAX_AGE_HOURS

Default items per feed: 15.
Override with:
  KAIVOR_NEWS_ITEMS_PER_FEED

Default parallel workers: 12.
Override with:
  KAIVOR_NEWS_MAX_WORKERS

IMPORTANT
---------
Do not include config/news_secrets.json or runtime saved-data files in project
snapshots or source bundles.


FP017.1 FOOTBALL-FIRST CORRECTION
- Sport category now prioritises football when the Sport tab is selected.
- Football focus survives article normalisation.
- Guardian/API/custom Sport items are classified for football relevance.
- Other sports remain available below football.
- Global Top Stories ordering is unchanged.
