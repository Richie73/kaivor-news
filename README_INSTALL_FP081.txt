KAIVOR FP081 — READING AND LISTENING LINKS IN THE READING TAB
===========================================================

PURPOSE
-------
The Reading tab now has a "Where I read & listen" section with
tap-to-open links for BorrowBox, Libby (OverDrive), Kindle and
Audible. Tap one and it opens the service — in its app, if the
app is installed on the phone. The links appear after unlocking
with the Reading PIN, like the rest of the tab.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. These are links out, not connections: no provider password is
   requested or stored, and loans, due dates and progress do
   not sync into Kaivor.
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
Replacement (back up the old copy as *.before-fp081 first):
- templates/reading.html

New:
- tests/test_reading_links_fp081.py
- CHANGELOG_FP081.txt
- README_INSTALL_FP081.txt
- BUNDLE_MANIFEST_FP081.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_reading_links_fp081.py tests/test_reading_web_fp042.py -q
   Expect: 10 passed.

2. Full suite:
   python -m pytest -q
   Expect: 548 passed, 0 failed, 2 skipped (545 + 3 new).

PUSH
----
   cd ~/Kaivor
   git add templates/reading.html tests/test_reading_links_fp081.py CHANGELOG_FP081.txt README_INSTALL_FP081.txt BUNDLE_MANIFEST_FP081.txt
   git status --short
   git commit -m "FP081: reading and listening links in the Reading tab"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, open the
📚 Reading tab, unlock with the PIN, and check the sidebar:
"Where I read & listen" with four links — BorrowBox, Libby
(OverDrive), Kindle and Audible. Tap one to confirm it opens
the service.
