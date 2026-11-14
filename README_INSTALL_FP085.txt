KAIVOR FP085 — SETTINGS GEAR + A MORE DYNAMIC OPENING ANIMATION
===============================================================

PURPOSE
-------
The feeds and API keys leave the home page for a proper Settings
screen behind a gear button in the header, holding everything
settings-shaped: adding a news source plus the list of feeds
Kaivor follows, all five API keys, the personal relevance
profile, and app status. The splash screen's opening animation
gets a shine sweep across the logo.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN
   or secret changes, no key rotation needed for this milestone.
2. Install AFTER FP084 is pushed. Both milestones replace
   templates/index.html — install FP085 only once the FP084
   commit is on GitHub, so the two milestones stay separate.
3. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
New:
- tests/test_settings_fp085.py
- CHANGELOG_FP085.txt
- README_INSTALL_FP085.txt
- BUNDLE_MANIFEST_FP085.txt

Replacement (back up the old copies as *.before-fp085 first):
- templates/index.html
- tests/test_bottom_nav_fp084.py
- tests/test_mobile_category_rail_fp067c.py
- tests/test_swipe_dispatch_fp072.py
- tests/test_weather_redesign_fp082.py
- tests/test_mobile_news_navigation_fp066.py
- tests/test_logo_splash_fp083.py

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_settings_fp085.py tests/test_bottom_nav_fp084.py tests/test_mobile_category_rail_fp067c.py tests/test_swipe_dispatch_fp072.py tests/test_weather_redesign_fp082.py tests/test_mobile_news_navigation_fp066.py tests/test_logo_splash_fp083.py -q
   Expect: 53 passed (8 FP085 + 8 FP084 + 5 FP067c + 5 FP072 + 11 FP082 + 7 FP066 + 9 FP083).

2. Full suite:
   python -m pytest -q
   Expect: 584 passed, 0 failed, 2 skipped (576 + 8 new).

PUSH
----
   cd ~/Kaivor
   git add templates/index.html tests/test_settings_fp085.py tests/test_bottom_nav_fp084.py tests/test_mobile_category_rail_fp067c.py tests/test_swipe_dispatch_fp072.py tests/test_weather_redesign_fp082.py tests/test_mobile_news_navigation_fp066.py tests/test_logo_splash_fp083.py CHANGELOG_FP085.txt README_INSTALL_FP085.txt BUNDLE_MANIFEST_FP085.txt
   git status --short
   git commit -m "FP085: settings gear + dynamic splash"
   git push

DEPLOY + TEST
-------------
Deploy on Render the normal way. Then, in the app:
- Reload: the logo shines as the splash opens, then fades.
- The home page no longer has the Sources & API Settings block.
- Tap ⚙️ Settings in the header: News sources (add form + your
  feeds list with working/broken status), API keys, Personal
  relevance and About Kaivor all show.
- Tap News in the bottom bar: the stories come straight back.
