KAIVOR FP079.2 — STOP THE CHAT REFUSING WEB QUESTIONS
====================================================

PURPOSE
-------
The web search works (FP079.1 proved it live), but the model
still answered "I don't have access to live internet data"
because the search snippets did not include the actual price.
This fix tells it the results ARE its internet access, so it
uses them and points at the live sources instead of refusing.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. Built and shipped together with FP080 (Market Watch prices in
   the chat). Both change main.py; install and push them as one
   commit (see the FP080 README for the combined push).

FILES
-----
Replacement (back up the old copy as *.before-fp0792 first):
- main.py (shared with FP080)

New:
- tests/test_chat_web_prompt_fp0792.py
- CHANGELOG_FP079.2.txt
- README_INSTALL_FP079.2.txt
- BUNDLE_MANIFEST_FP079.2.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_web_prompt_fp0792.py tests/test_chat_market_fp080.py tests/test_chat_web_status_fp0791.py tests/test_chat_web_fp079.py -q
   Expect: 31 passed.

2. Full suite:
   python -m pytest -q
   Expect: 533 passed, 0 failed, 2 skipped (520 + 13 new).

PUSH
----
See the FP080 README for the combined push (one commit, both
milestones).

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app, unlock via
the 📚 Reading tab, open 💬 Chat, switch 🌐 Web on, and ask
"Gold price right now". Expect a reply that uses the results
and points at the sources — and, with FP080, the actual price
from Market Watch (tap "Refresh markets" on the homepage first
if the market data has not loaded since the restart).
