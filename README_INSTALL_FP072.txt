KAIVOR FP072 — FIX THE CATEGORY SWIPE
=====================================

PURPOSE
-------
On 13 Nov 2026, after the FP068/69 redeploy, swiping left or right on
the news page stopped changing category. Cause: the swipe code tried
to read the category name off each button with a pattern that did not
match the buttons (they carry an extra `,this` the pattern did not
allow for), so every swipe silently did nothing.

This milestone fixes it by making the swipe tap the next button
instead of trying to read its name — the same thing a finger tap
does. Nothing else about the swipe changes: same 75px threshold, same
vertical-gesture guard, same 13 destinations (10 categories + Saved +
Relevance + Reading).

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. The chip bar's own drag-scroll is untouched — it was never broken.

FILES
-----
Replacement (back up the old copies as *.before-fp072 first):
- templates/index.html
- tests/test_mobile_category_swipe_all_navigation_fp067d.py
- tests/test_mobile_news_navigation_fp066.py
- tests/test_mobile_category_title_fp067.py

New:
- tests/test_swipe_dispatch_fp072.py
- README_INSTALL_FP072.txt
- CHANGELOG_FP072.txt
- BUNDLE_MANIFEST_FP072.txt

INSTALL (TERMUX)
----------------
The install is done over SSH by Muse (the usual FP068/FP069 pattern):
copies are transferred, checksummed, and the replaced files are backed
up as *.before-fp072. No files are deleted.

VERIFY (TERMUX)
---------------
Run the targeted tests, then the full suite:

  cd ~/Kaivor
  python3 -m pytest tests/test_swipe_dispatch_fp072.py tests/test_mobile_category_swipe_all_navigation_fp067d.py tests/test_mobile_news_navigation_fp066.py tests/test_mobile_category_rail_fp067b.py tests/test_mobile_category_rail_fp067c.py -q
  python3 -m pytest -q

Expected: the targeted run passes fully, and the full suite passes
with 0 failures on the phone.

Then check the fix by eye on the phone's own copy of the site
(after the Render deploy): open the live site, swipe left on a story
card, and the category should move one step (Top Stories -> World).

ROLLBACK
--------
Restore the backed-up files and restart the app:

  cd ~/Kaivor
  cp templates/index.html.before-fp072 templates/index.html
  cp tests/test_mobile_category_swipe_all_navigation_fp067d.py.before-fp072 tests/test_mobile_category_swipe_all_navigation_fp067d.py
  cp tests/test_mobile_news_navigation_fp066.py.before-fp072 tests/test_mobile_news_navigation_fp066.py
  cp tests/test_mobile_category_title_fp067.py.before-fp072 tests/test_mobile_category_title_fp067.py
  rm tests/test_swipe_dispatch_fp072.py

The old (broken) swipe dispatch returns.

DEPLOY
------
After the Termux install and checks pass, commit and push the normal
way (Richie runs the push from Termux). Then CHECK the Render
dashboard: the FP071 push on 13 Nov did NOT auto-deploy, and the new
version only went live after a manual deploy from the dashboard
(Deploy -> Deploy latest commit). If no deploy starts within a few
minutes of the push, deploy it manually. After the deploy, the swipe
should work on the live site; the news feed refills within a few
minutes of the restart.
