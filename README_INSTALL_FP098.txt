KAIVOR FP098 — TWO LIVE-CHECK FIXES
==================================

PURPOSE
-------
Two bugs found by the polish-round live check on 15 Nov 2026:
(1) a literal "&nbsp;" showing in a card description;
(2) the "why it matters" line calling Russell Brand stories a
motorsport development. Both fixed.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP097 is installed.
4. The fixes apply to stories as they refresh — the next news
   refresh after deploy re-normalises every article, so the
   "&nbsp;" and the wrong significance lines disappear with it.
   Stories already saved keep their old text until re-saved.

FILES
-----
New:
- tests/test_impact_hints_fp098.py
- tests/test_description_entities_fp098.py
- CHANGELOG_FP098.txt
- README_INSTALL_FP098.txt
- BUNDLE_MANIFEST_FP098.txt

Replacement (back up the old copies as *.before-fp098 first):
- news_store.py
- story_intelligence.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_impact_hints_fp098.py tests/test_description_entities_fp098.py -q
   Expect: 13 passed.

2. Full suite:
   python -m pytest -q
   Expect: 723 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add news_store.py story_intelligence.py tests/test_impact_hints_fp098.py tests/test_description_entities_fp098.py CHANGELOG_FP098.txt README_INSTALL_FP098.txt BUNDLE_MANIFEST_FP098.txt
   git status --short
   git commit -m "FP098: decode entities in titles/descriptions; whole-word impact keywords + motorsport surname context"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way and wait for the next news
refresh (a couple of minutes). Then check a Russell Brand story
— its "why it matters" line should no longer mention motorsport
— and the Anthropic IPO card, whose description should read
normally with no "&nbsp;" showing.
