README_INSTALL_FP125.txt — Shopping hub (watchlist card in the Hub)
==================================================================

1. Run the migration FIRST (before pushing): in the Supabase
   SQL Editor, connected to KaivorDatabase, run the single
   statement in migrations/reading/004_shopping_items_fp125.sql.
   It creates public.shopping_items. On the phone, delete the
   stray ")" the editor appends below the pasted block before
   tapping Run. Until this runs, the Hub card says shopping
   isn't set up yet.

2. Install: copy these files over the matching files in
   ~/Kaivor, then run the targeted tests:

     cd ~/Kaivor
     python -m pytest tests/test_shopping_hub_fp125.py -q

   Expected: 40 passed. Full suite: 1080 passed / 0 failed /
   2 skipped.

3. Deploy as usual. First open of the Hub seeds the five
   watchlist items (Tapo TC85 x3, Sofirn SC33, Rammstein Zeit
   vinyl, Pixel 11 Pro EE deal, Fire TV Stick 4K Max).
   "Check prices" re-checks the checkable items only (today:
   just the Fire TV Stick — the rest are manual by design).
