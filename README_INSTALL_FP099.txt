KAIVOR FP099 — VOICE INPUT IN CHAT
=================================

PURPOSE
-------
Talk to Kaivor instead of typing. A microphone button in the
chat form uses the browser's built-in speech recognition — free,
no key, nothing new to set up. The words land in the input and
you tap Send as normal.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP098 is installed.

FILES
-----
New:
- tests/test_voice_input_fp099.py
- CHANGELOG_FP099.txt
- README_INSTALL_FP099.txt
- BUNDLE_MANIFEST_FP099.txt

Replacement (back up the old copy as *.before-fp099 first):
- templates/index.html

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_voice_input_fp099.py -q
   Expect: 6 passed.

2. Full suite:
   python -m pytest -q
   Expect: 729 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_voice_input_fp099.py CHANGELOG_FP099.txt README_INSTALL_FP099.txt BUNDLE_MANIFEST_FP099.txt
   git status --short
   git commit -m "FP099: voice input in chat via browser speech recognition"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then open Chat, tap the 🎤
button and speak — allow the microphone if the browser asks.
Your words should appear in the input; tap Send as normal. The
button turns red while listening; tap it again to stop.
