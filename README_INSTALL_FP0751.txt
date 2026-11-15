KAIVOR FP075.1 — SHARPER PICTURES: BBC THUMBNAILS UPGRADED
=========================================================

PURPOSE
-------
Fix for the blurry pictures Richie reported on 15 Nov 2026.
The BBC's feeds serve tiny 240px-wide thumbnails — and the
BBC is the biggest image source in the feed (96 of 400 cards).
The BBC's image service takes the width in the URL, so the
app now asks for 1024px instead. Every other source already
serves large images (Guardian 700px, NYT 1800px, Sky 1920px),
so only the BBC needed fixing.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. The sharper pictures appear after the next news refresh
   (the feed refreshes itself; a redeploy wipes the cache and
   the fresh articles come in with the bigger pictures).

FILES
-----
New:
- CHANGELOG_FP0751.txt
- README_INSTALL_FP0751.txt
- BUNDLE_MANIFEST_FP0751.txt

Replacement (back up the old copies as *.before-fp0751 first):
- news_store.py
- tests/test_story_images_fp075.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_story_images_fp075.py -q
   Expect: 14 passed.

2. Full suite:
   python -m pytest -q
   Expect: 674 passed, 0 failed, 2 skipped (673 + 1 new).

PUSH
----
   cd ~/Kaivor
   git add news_store.py tests/test_story_images_fp075.py CHANGELOG_FP0751.txt README_INSTALL_FP0751.txt BUNDLE_MANIFEST_FP0751.txt
   git status --short
   git commit -m "FP075.1: BBC thumbnails upgraded to 1024px"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, scroll the
news and check the BBC pictures — they should look sharp now,
not blurry. (The feed refreshes itself after the deploy; give
it a minute or two.)
