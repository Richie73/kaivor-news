KAIVOR FP075 — STORY PICTURES
=============================

PURPOSE
-------
News cards now show the picture the publisher chose for that story
— the same lead image you'd see on the publisher's own site. Most
stories from the big publishers will have one; a few feeds don't
send a picture, and those cards stay exactly as they are.

No new API calls, no new keys, no cost. The pictures arrive with
the news the app already fetches.

IMPORTANT NOTES
---------------
1. No configuration changes. No new environment variables, no PIN or
   secret changes, no key rotation needed for this milestone.
2. This milestone does not deploy anything by itself. Install in
   Termux first and run the checks below. Then push to GitHub the
   normal way and deploy on Render (see DEPLOY below).
3. Pictures load from the publishers' own servers. If one fails to
   load it quietly disappears — no broken-image icon.
4. Saving a story keeps its picture, and the Saved view shows it too.

FILES
-----
Replacement (back up the old copies as *.before-fp075 first):
- news_freshness.py (RSS image extraction)
- news_store.py (image_url kept through normalisation)
- main.py (Guardian thumbnail + NewsData image_url)
- templates/index.html (card image, Saved view, save keeps image)

New:
- tests/test_story_images_fp075.py
- CHANGELOG_FP075.txt
- README_INSTALL_FP075.txt
- BUNDLE_MANIFEST_FP075.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_story_images_fp075.py -q
   Expect: 13 passed.

2. Full suite:
   python -m pytest -q
   Expect: 482 passed, 0 failed, 2 skipped (469 + 13 new).

3. Quick live check (needs the app running):
   curl -s http://localhost:5000/ | grep -o 'class="card-image"' | head -3
   Expect: at least one match once the feed has refreshed (a fresh
   refresh is needed — pictures only arrive with new articles).

DEPLOY
------
After the Termux checks pass:

   cd ~/Kaivor
   git add news_freshness.py news_store.py main.py templates/index.html tests/test_story_images_fp075.py CHANGELOG_FP075.txt README_INSTALL_FP075.txt BUNDLE_MANIFEST_FP075.txt
   git status --short
   git commit -m "FP075: story pictures — publisher images on news cards"
   git push

Then deploy in the Render dashboard (Deploy -> Deploy latest commit)
if auto-deploy does not start on its own. Tell Muse when it is live
and the pictures will be checked on the live site.
