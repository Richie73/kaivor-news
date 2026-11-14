KAIVOR FP079.1 — WEB STATUS INDICATOR FOR THE CHAT HUB
=====================================================

PURPOSE
-------
After FP079, web questions came back as plain replies with no
Sources list and no explanation. This small fix makes the web
state visible, so the next test shows exactly what happened:

- Your question gets a small 🌐 badge when web was on as you
  sent it. No badge means the toggle was off when you pressed
  Send.
- Under the reply, a grey line says what the search did:
  "🌐 Web search · 5 sources", "🌐 Web search found nothing.",
  or "🌐 Web: the app server hasn't updated yet".
- The server also writes one line per chat message into the
  Render Logs, showing whether web was requested and how many
  sources came back. No message text is logged.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
Replacement (back up the old copy as *.before-fp0791 first):
- main.py
- templates/index.html

New:
- tests/test_chat_web_status_fp0791.py
- CHANGELOG_FP079.1.txt
- README_INSTALL_FP079.1.txt
- BUNDLE_MANIFEST_FP079.1.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_web_status_fp0791.py tests/test_chat_web_fp079.py -q
   Expect: 18 passed.

2. Full suite:
   python -m pytest -q
   Expect: 520 passed, 0 failed, 2 skipped (515 + 5 new).

PUSH
----
   cd ~/Kaivor
   git add main.py templates/index.html tests/test_chat_web_status_fp0791.py CHANGELOG_FP079.1.txt README_INSTALL_FP079.1.txt BUNDLE_MANIFEST_FP079.1.txt
   git status --short
   git commit -m "FP079.1: web status indicator for the chat hub"
   git push

DEPLOY + DIAGNOSTIC TEST
------------------------
Deploy on Render the normal way. Then, in the app:

1. Unlock via the 📚 Reading tab, open 💬 Chat, switch 🌐 Web
   on, and ask "Gold price right now".
2. Look for three things and report them back:
   a. Does your question have a small 🌐 badge?
   b. What does the grey line under the reply say?
   c. In the Render dashboard, kaivor-news, Logs tab: find the
      newest line starting "[chat]" and report what it says.
