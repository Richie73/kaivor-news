KAIVOR FP094 — CLICKABLE LINKS IN CHAT
====================================

PURPOSE
-------
Web addresses the chat gives used to show as plain text you
could not tap. Markdown links and bare URLs now render as links
opening in a new tab.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP093 is installed.

FILES
-----
New:
- tests/test_chat_links_fp094.py
- CHANGELOG_FP094.txt
- README_INSTALL_FP094.txt
- BUNDLE_MANIFEST_FP094.txt

Replacement (back up the old copy as *.before-fp094 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_links_fp094.py -q
   Expect: 3 passed.

2. Full suite:
   python -m pytest -q
   Expect: 694 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_chat_links_fp094.py CHANGELOG_FP094.txt README_INSTALL_FP094.txt BUNDLE_MANIFEST_FP094.txt
   git status --short
   git commit -m "FP094: clickable links in chat replies"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then ask the chat (with web on)
for a story with a link — the link in its reply should be
tappable and open in a new tab.
