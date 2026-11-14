KAIVOR FP079 — WEB BROWSING IN THE CHAT HUB
==========================================

PURPOSE
-------
The 💬 Chat tab can now look things up on the web before
answering. Switch the 🌐 Web toggle on next to Send, ask
something that needs live information (a score, a price, today's
news), and Kaivor searches first, then answers from the results
with a Sources list under the reply.

- The toggle is off by default and remembered on the device.
- Web search uses the Brave key the app already has — nothing
  new to set up. If no Brave key is configured, chat says so
  instead of searching.
- When the search finds nothing, chat answers normally and says
  no results were found.
- Sources are saved with the reply, so they are still there when
  you reopen the chat.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. Web search costs one Brave query per web question. The AI
   reply itself costs the same as any other chat message.

FILES
-----
Replacement (back up the old copy as *.before-fp079 first):
- main.py
- templates/index.html

New:
- tests/test_chat_web_fp079.py
- CHANGELOG_FP079.txt
- README_INSTALL_FP079.txt
- BUNDLE_MANIFEST_FP079.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_chat_web_fp079.py -q
   Expect: 13 passed.

2. Full suite:
   python -m pytest -q
   Expect: 515 passed, 0 failed, 2 skipped (502 + 13 new).

PUSH
----
   cd ~/Kaivor
   git add main.py templates/index.html tests/test_chat_web_fp079.py CHANGELOG_FP079.txt README_INSTALL_FP079.txt BUNDLE_MANIFEST_FP079.txt
   git status --short
   git commit -m "FP079: web browsing in the chat hub"
   git push

DEPLOY
------
Deploy on Render the normal way (auto-deploy usually fires; if
not, Deploy -> Deploy latest commit in the dashboard). Then
verify: open the app, unlock via the 📚 Reading tab, open the
💬 Chat tab, switch 🌐 Web on, and ask something with a live
answer (for example "Who won the football last night?"). Expect
a reply with a Sources list underneath.
