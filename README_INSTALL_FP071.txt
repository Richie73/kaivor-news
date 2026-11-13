KAIVOR FP071 — MAKE THE NEWS REFRESH RELIABLE ON SLOW HOSTS
============================================================

PURPOSE
-------
On 13 Nov 2026 the live site's news went empty after the FP068/69
redeploy and stayed empty. Two causes, found one after the other:

1. The refresh crashed at the NewsData step (AttributeError) because
   the deployed config/secrets.py did not define get_provider_key.
   Fixed by committing the rewritten config/secrets.py (1591379).
2. With the crash gone, the refresh ran past the 90-second limit the
   app gives the collection step and was killed. The phone does the
   whole refresh in ~34 seconds, but Render's free tier is slower and
   needs ~85-100 seconds, so healthy refreshes were cut off.

This milestone fixes the second cause and hardens the first:
- The collection step now gets 240 seconds instead of 90.
- A NewsData credential problem now degrades to zero NewsData articles
  instead of killing the whole refresh.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and Render redeploys automatically.
3. The 240-second limit only affects the background refresh. It does
   not slow down page loads or the market refresh.

FILES
-----
Replacement (back up the old copies as *.before-fp071 first):
- main.py
- tests/test_news_refresh_isolation.py

New:
- tests/test_refresh_reliability_fp071.py
- README_INSTALL_FP071.txt
- CHANGELOG_FP071.txt
- BUNDLE_MANIFEST_FP071.txt

INSTALL (TERMUX)
----------------
The install is done over SSH by Muse (the usual FP068/FP069 pattern):
copies are transferred, checksummed, and the replaced files are backed
up as *.before-fp071. No files are deleted.

VERIFY (TERMUX)
---------------
Run the targeted tests, then the full suite:

  cd ~/Kaivor
  python3 -m pytest tests/test_refresh_reliability_fp071.py tests/test_news_refresh_isolation.py tests/test_newsdata.py -q
  python3 -m pytest -q

Expected: the targeted run passes fully on the phone (the 3 NewsData
tests that fail locally against the test-only stub pass on the phone,
where the real config/secrets.py reads the environment). The full
suite should pass with 0 failures on the phone.

Then run the refresh end to end and confirm it completes:

  python3 news_refresh_runner.py > ~/refresh-test-fp071.json 2> ~/refresh-test-fp071.log; echo exit=$?

Expected: exit=0 and several hundred articles in the JSON output.

ROLLBACK
--------
Restore the backed-up files and restart the app:

  cd ~/Kaivor
  cp main.py.before-fp071 main.py
  cp tests/test_news_refresh_isolation.py.before-fp071 tests/test_news_refresh_isolation.py
  rm tests/test_refresh_reliability_fp071.py

The 90-second limit and the old NewsData behaviour return. (The
config/secrets.py fix from 1591379 is separate and stays.)

DEPLOY
------
After the Termux install and checks pass, commit and push the normal
way (Richie runs the push from Termux). Render redeploys automatically
on push to main. The next refresh after the redeploy should complete
and the stories should come back within a few minutes. Check with:

  https://kaivor-news.onrender.com/api/health
  (news_count above 0, cron_refresh_last_successful recent)

and the homepage Top Stories.
