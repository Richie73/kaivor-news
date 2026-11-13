KAIVOR FP076 — MORE PUZZLES
==========================

PURPOSE
-------
The Puzzles category had only 4 puzzles. It now has 12:

- NYT Connections and NYT Strands (new daily word games)
- Quordle (4 Wordles at once)
- Nerdle (Wordle with numbers)
- Sudoku.com (daily Sudoku)
- Lichess puzzles (chess, from real games)
- Worldle (guess the country from its shape)
- Waffle (swap letters to make six words)

All free to play, no account needed for the daily puzzle. Every
link was checked live before it was added.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).

FILES
-----
Replacement (back up the old copy as *.before-fp076 first):
- main.py (8 new puzzle entries)

New:
- tests/test_puzzles_fp076.py
- CHANGELOG_FP076.txt
- README_INSTALL_FP076.txt
- BUNDLE_MANIFEST_FP076.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_puzzles_fp076.py -q
   Expect: 4 passed.

2. Full suite:
   python -m pytest -q
   Expect: 486 passed, 0 failed, 2 skipped (482 + 4 new).

DEPLOY
------
After the Termux checks pass:

   cd ~/Kaivor
   git add main.py tests/test_puzzles_fp076.py CHANGELOG_FP076.txt README_INSTALL_FP076.txt BUNDLE_MANIFEST_FP076.txt
   git status --short
   git commit -m "FP076: more puzzles — 12 in the Puzzles category"
   git push

Then deploy in the Render dashboard (Deploy -> Deploy latest commit)
if auto-deploy does not start on its own. Tell Muse when it is live
and the puzzles will be checked on the live site.
