KAIVOR FP087 — NEWS CARDS: CONSISTENT CROPS, LABELS, TIMESTAMPS
=============================================================

PURPOSE
-------
First of the polish pass: every news card's picture is now the same
16:9 shape, the category/provider/source labels sit on one line,
and the timestamp is styled in one place instead of inline.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- tests/test_news_cards_fp087.py
- CHANGELOG_FP087.txt
- README_INSTALL_FP087.txt
- BUNDLE_MANIFEST_FP087.txt

Replacement (back up the old copy as *.before-fp087 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_news_cards_fp087.py -q
   Expect: 5 passed.

2. Full suite:
   python -m pytest -q
   Expect: 612 passed, 0 failed, 2 skipped (607 + 5 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_news_cards_fp087.py CHANGELOG_FP087.txt README_INSTALL_FP087.txt BUNDLE_MANIFEST_FP087.txt
   git status --short
   git commit -m "FP087: news cards — consistent crops, labels, timestamps"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Scroll the news: every pictured story's image is the same shape.
- Each card's category, provider and source sit on one line.
- The date under each headline looks the same on every card.
