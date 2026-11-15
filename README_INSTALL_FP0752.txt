KAIVOR FP075.2 — SHARPER PICTURES: THE OTHER BBC IMAGE FORM
===========================================================

PURPOSE
-------
Follow-up to FP075.1. Its live check found 95 of the 96 BBC
pictures upgraded to 1024px — one card uses the BBC's newer
image URL form (/images/ic/240x135/) which FP075.1 did not
cover. This milestone rewrites that form to 1024x576 too.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP075.1 is pushed.

FILES
-----
New:
- CHANGELOG_FP0752.txt
- README_INSTALL_FP0752.txt
- BUNDLE_MANIFEST_FP0752.txt

Replacement (back up the old copies as *.before-fp0752 first):
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
   Expect: 674 passed, 0 failed, 2 skipped (unchanged — no new
   test function, one assertion added to the FP075.1 test).

PUSH
----
   cd ~/Kaivor
   git add news_store.py tests/test_story_images_fp075.py CHANGELOG_FP0752.txt README_INSTALL_FP0752.txt BUNDLE_MANIFEST_FP0752.txt
   git status --short
   git commit -m "FP075.2: BBC images/ic form upgraded to 1024x576"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, scroll the
news — every BBC picture should look sharp now.
