KAIVOR FP084 — BOTTOM NAVIGATION BAR + NEWS-ONLY CATEGORY RAIL
===============================================================

PURPOSE
-------
The fifteen-destination top rail is split: a fixed bottom bar
holds the five main destinations (News, Weather, Chat, Saved,
Reading), always visible and one tap away, and the top rail keeps
only the ten news categories. Relevance moves to a button in the
header. Swiping moves between news categories only. The Reading
tab gets the same bottom bar.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. Install AFTER FP083 is pushed. Both milestones replace
   templates/index.html and templates/reading.html — install FP084
   only once the FP083 commit is on GitHub, so the two milestones
   stay separate.
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- tests/test_bottom_nav_fp084.py
- CHANGELOG_FP084.txt
- README_INSTALL_FP084.txt
- BUNDLE_MANIFEST_FP084.txt

Replacement (back up the old copies as *.before-fp084 first):
- templates/index.html
- templates/reading.html
- tests/test_mobile_category_rail_fp067b.py
- tests/test_mobile_category_rail_fp067c.py
- tests/test_mobile_category_swipe_all_navigation_fp067d.py
- tests/test_swipe_dispatch_fp072.py
- tests/test_weather_redesign_fp082.py
- tests/test_chat_hub_fp077.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_bottom_nav_fp084.py tests/test_mobile_category_rail_fp067b.py tests/test_mobile_category_rail_fp067c.py tests/test_mobile_category_swipe_all_navigation_fp067d.py tests/test_swipe_dispatch_fp072.py tests/test_weather_redesign_fp082.py tests/test_chat_hub_fp077.py -q
   Expect: 49 passed (8 FP084 + 7 FP067b + 5 FP067c + 5 FP067d + 5 FP072 + 11 FP082 + 8 FP077).

2. Full suite:
   python -m pytest -q
   Expect: 576 passed, 0 failed, 2 skipped (568 + 8 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html templates/reading.html tests/test_bottom_nav_fp084.py tests/test_mobile_category_rail_fp067b.py tests/test_mobile_category_rail_fp067c.py tests/test_mobile_category_swipe_all_navigation_fp067d.py tests/test_swipe_dispatch_fp072.py tests/test_weather_redesign_fp082.py tests/test_chat_hub_fp077.py CHANGELOG_FP084.txt README_INSTALL_FP084.txt BUNDLE_MANIFEST_FP084.txt
   git status --short
   git commit -m "FP084: bottom nav bar + news-only rail"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- A bottom bar shows News, Weather, Chat, Saved, Reading; the
  active one is green.
- The top rail holds only the ten news categories.
- Tap Weather, Chat, Saved in the bar: each view opens, and the
  bar highlights it. Tap News: the stories come back.
- Swipe left/right on the stories: it moves between news
  categories only.
- The 🎯 Relevance button is in the header.
- Open the Reading tab: same bottom bar, Reading highlighted;
  tapping Weather there opens the news page straight into the
  weather view.
- Scroll to the bottom of a long list: the last card is not
  hidden behind the bar, and the ↑ button still floats above it.
