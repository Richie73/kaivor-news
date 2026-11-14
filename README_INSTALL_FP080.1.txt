KAIVOR FP080.1 — ANSWER PRICE QUESTIONS DIRECTLY
================================================

PURPOSE
-------
The chat kept refusing price questions even with the figures in
front of it, because the model would not follow the prompt. This
fix takes the model out of it: a plain price question ("Gold
price right now", "Give me the live gold price") is now answered
straight from the app's Market Watch data, with no AI call at
all — so it cannot refuse, and it costs nothing. Longer
questions ("should I buy?", "is gold up today?") still go to
the AI as before.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
Replacement (back up the old copy as *.before-fp0801 first):
- main.py
- tests/test_chat_market_fp080.py (route tests now use broader
  questions so they exercise the model path)
- tests/test_chat_web_prompt_fp0792.py (same, one test)

New:
- tests/test_chat_market_direct_fp0801.py
- CHANGELOG_FP080.1.txt
- README_INSTALL_FP080.1.txt
- BUNDLE_MANIFEST_FP080.1.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_market_direct_fp0801.py tests/test_chat_market_fp080.py tests/test_chat_web_prompt_fp0792.py tests/test_chat_web_status_fp0791.py tests/test_chat_web_fp079.py -q
   Expect: 43 passed.

2. Full suite:
   python -m pytest -q
   Expect: 545 passed, 0 failed, 2 skipped (533 + 12 new).

PUSH
----
   cd ~/Kaivor
   git add main.py tests/test_chat_market_direct_fp0801.py tests/test_chat_market_fp080.py tests/test_chat_web_prompt_fp0792.py CHANGELOG_FP080.1.txt README_INSTALL_FP080.1.txt BUNDLE_MANIFEST_FP080.1.txt
   git status --short
   git commit -m "FP080.1: answer price questions directly from Market Watch"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:

1. On the homepage, tap "Refresh markets" and wait for the
   numbers to appear (the market data clears on every restart,
   so load it before testing).
2. Unlock via the 📚 Reading tab, open 💬 Chat, and ask
   "Give me the live gold price". Expect the price with its
   fetch time, straight away — with or without 🌐 Web on.
