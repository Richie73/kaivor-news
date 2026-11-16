FP110 INSTALL — Live football scores (Premier League + England)
================================================================
Files (4 code/test + 3 docs):
  football_scores.py (new)
  main.py
  templates/index.html
  tests/test_live_scores_fp110.py
  CHANGELOG_FP110.txt
  README_INSTALL_FP110.txt
  BUNDLE_MANIFEST_FP110.txt

HOLD — DO NOT INSTALL until FP106, FP107 and FP108 are all pushed.
FP110 shares main.py and templates/index.html with FP106, and its
main.py also carries FP108's provider-layer wiring. Installing early
would contaminate those pushes (an FP106-only push carrying this
main.py would ImportError on football_scores, which is not in the
repo yet).

Install (Termux, from ~/Kaivor), after the hold clears:
  1. Back up the files being changed:
       cp main.py main.py.before-fp110
       cp templates/index.html templates/index.html.before-fp110
  2. Copy the new files in (Muse installs them over SSH).
  3. Run the targeted tests:
       python -m pytest tests/test_live_scores_fp110.py -q
     Expected: 17 passed.
  4. Run the full suite:
       python -m pytest -q
     Expected: 873 passed, 0 failed, 2 skipped.

Push:
  cd ~/Kaivor
  git add football_scores.py main.py templates/index.html tests/test_live_scores_fp110.py CHANGELOG_FP110.txt README_INSTALL_FP110.txt BUNDLE_MANIFEST_FP110.txt
  git status --short
  git commit -m "FP110: live football scores (Premier League and England) in the Sport view"
  git push

Live check after deploy: GET /api/football/scores returns the
gameweek's fixtures; in Kaivor, tap the Sport chip and the scores
strip appears above the stories (on a non-matchday it shows the
coming fixtures with kickoff times). England's section appears only
when England have a fixture in the feed's window.
