KAIVOR FP102 — RECEIPT CAPTURE
==============================

PURPOSE
-------
Photograph a receipt and Kaivor reads the shop, date and total
with AI vision, then saves the checked details as an expense.
Opened from the Morning Hub. Each scan costs about a tenth of a
penny from your OpenRouter credit.

IMPORTANT NOTES
---------------
1. No configuration changes are needed: scanning uses the
   OpenRouter key already set on the server. No PIN or secret
   changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see PUSH below).
3. SEQUENCING: install only after FP101 is installed. (FP100 is
   still waiting on the RAMS template answer.)

FILES
-----
New:
- receipt_reader.py
- tests/test_receipt_capture_fp102.py
- CHANGELOG_FP102.txt
- README_INSTALL_FP102.txt
- BUNDLE_MANIFEST_FP102.txt

Replacement (back up the old copy as *.before-fp102 first):
- news_store.py
- main.py
- templates/index.html
- tests/test_weather_redesign_fp082.py
- tests/test_markets_view_fp086.py
- tests/test_morning_hub_fp101.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse.
The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_receipt_capture_fp102.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py -q
   Expect: 40 passed.

2. Full suite:
   python -m pytest -q
   Expect: 748 passed, 0 failed, 2 skipped.

PUSH
----
   cd ~/Kaivor
   git add receipt_reader.py news_store.py main.py templates/index.html tests/test_receipt_capture_fp102.py tests/test_weather_redesign_fp082.py tests/test_markets_view_fp086.py tests/test_morning_hub_fp101.py CHANGELOG_FP102.txt README_INSTALL_FP102.txt BUNDLE_MANIFEST_FP102.txt
   git status --short
   git commit -m "FP102: receipt capture — scan with AI vision, save as expense"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Unlock via the 📚 Reading tab
first (scanning needs the app unlocked), then open the Hub and
tap "🧾 Scan a receipt". Photograph a receipt: the shop, date
and total should appear for checking — correct anything wrong,
then Save. The expense appears in the list below with a running
total, and Download CSV gives you a spreadsheet-ready file.
