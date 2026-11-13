KAIVOR FP077 — GENERAL CHAT HUB
==============================

PURPOSE
-------
A 💬 Chat tab in the app: ask Kaivor anything — not just about a
story. It remembers the conversation (on your device only) so you
can ask follow-up questions.

- Open it from the 💬 Chat chip, or swipe across to it like any
  other section.
- Your messages are green on the right, Kaivor's are dark on the
  left.
- The conversation is saved on the device you are using. Clear chat
  wipes it.
- It uses the same AI key as Ask AI — nothing new to set up. If the
  app is locked, chat tells you to unlock via the 📚 Reading tab
  first (same PIN).

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. Chat history does not move between devices: what you ask on your
   phone stays on your phone, and the computer has its own separate
   conversation.

FILES
-----
Replacement (back up the old copies as *.before-fp077 first):
- main.py (new /api/chat route, added to the PIN gate)
- templates/index.html (Chat chip, chat view, swipe destination)
- tests/test_news_mutation_auth_fp069.py (/api/chat in the guarded list)
- tests/test_mobile_category_swipe_all_navigation_fp067d.py (chat in swipe destinations)

New:
- tests/test_chat_hub_fp077.py
- CHANGELOG_FP077.txt
- README_INSTALL_FP077.txt
- BUNDLE_MANIFEST_FP077.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_hub_fp077.py tests/test_news_mutation_auth_fp069.py tests/test_mobile_category_swipe_all_navigation_fp067d.py -q
   Expect: 54 passed.

2. Full suite:
   python -m pytest -q
   Expect: 497 passed, 0 failed, 2 skipped (486 + 11 new).

DEPLOY
------
After the Termux checks pass (FP076 and FP077 go up together —
two commits, one push):

   cd ~/Kaivor
   git add main.py tests/test_puzzles_fp076.py CHANGELOG_FP076.txt README_INSTALL_FP076.txt BUNDLE_MANIFEST_FP076.txt
   git commit -m "FP076: more puzzles — 12 in the Puzzles category"
   git add main.py templates/index.html tests/test_chat_hub_fp077.py tests/test_news_mutation_auth_fp069.py tests/test_mobile_category_swipe_all_navigation_fp067d.py CHANGELOG_FP077.txt README_INSTALL_FP077.txt BUNDLE_MANIFEST_FP077.txt
   git status --short
   git commit -m "FP077: general chat hub"
   git push

Then deploy in the Render dashboard (Deploy -> Deploy latest commit)
if auto-deploy does not start on its own. Tell Muse when it is live
and the puzzles and chat will be checked on the live site.
