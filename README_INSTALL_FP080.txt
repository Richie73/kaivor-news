KAIVOR FP080 — MARKET WATCH PRICES IN THE CHAT HUB
=================================================

PURPOSE
-------
The chat can now answer price questions with real numbers from
the app's own Market Watch data: gold, bitcoin, S&P 500, Brent
oil, GBP/USD, GBP/EUR and EUR/USD. Ask "Gold price right now"
and the reply gives the stored price with the time it was
fetched. It works with web search on or off. If the market data
has not loaded since the app restarted, the reply tells you to
tap "Refresh markets" on the homepage first.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. Built and shipped together with FP079.2 (stop the chat
   refusing web questions). Both change main.py; install and push
   them as one commit.

FILES
-----
Replacement (back up the old copy as *.before-fp080 first):
- main.py (shared with FP079.2)

New:
- tests/test_chat_market_fp080.py
- CHANGELOG_FP080.txt
- README_INSTALL_FP080.txt
- BUNDLE_MANIFEST_FP080.txt

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

PUSH (one commit, both milestones)
----------------------------------
   cd ~/Kaivor
   git add main.py tests/test_chat_web_prompt_fp0792.py tests/test_chat_market_fp080.py CHANGELOG_FP079.2.txt README_INSTALL_FP079.2.txt BUNDLE_MANIFEST_FP079.2.txt CHANGELOG_FP080.txt README_INSTALL_FP080.txt BUNDLE_MANIFEST_FP080.txt
   git status --short
   git commit -m "FP079.2 + FP080: use web results and Market Watch prices in chat"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:

1. On the homepage, tap "Refresh markets" (the market data
   clears on every restart, so load it before testing).
2. Unlock via the 📚 Reading tab, open 💬 Chat, and ask
   "Gold price right now" — first with 🌐 Web off, then with
   it on. Expect the actual price with its fetch time in both
   replies, plus the Sources list when web is on.
