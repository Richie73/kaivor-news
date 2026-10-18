KAIVOR NEWS — FP022.0 RELIABILITY REGRESSION PROTECTION
======================================================

SCOPE
-----
This is a tests-and-validation milestone. It adds four regression tests for:
- preserving cache timestamps and diagnostics when fetching raises an exception;
- replacing the cache and refreshing aggregate quality diagnostics on success;
- preventing duplicate cron workers while a refresh is already running;
- allowing a new cron refresh after a cooldown has expired.

No production application files are replaced in this milestone.

CONTENTS
--------
tests/test_news_reliability_fp022.py
scripts/test_news_reliability.sh

INSTALL (TERMUX ONLY)
---------------------
From Termux, with the Kaivor News repository at ~/Kaivor:

1. Copy the two files from this ZIP, preserving their paths, into ~/Kaivor.
   If the ZIP is in Android shared storage, for example:

   cd ~/Kaivor
   unzip -o ~/storage/shared/Download/Kaivor-News-FP022.0-Reliability-Tests.zip \
     tests/test_news_reliability_fp022.py scripts/test_news_reliability.sh -d .

   Adjust the ZIP path only if you saved it somewhere else.

2. Run the complete validation command:

   cd ~/Kaivor && bash scripts/test_news_reliability.sh

   The script compiles the main news modules and tests, runs the full tests/
   suite, then checks whitespace errors. It does not deploy or change production.

3. If dependencies are missing, install the project's declared requirements:

   cd ~/Kaivor && python -m pip install -r requirements.txt

   Then repeat the validation command.

4. Review only the two intended additions:

   cd ~/Kaivor && git status --short
   git diff --check

   Do not use `git add .`. Stage the two files explicitly only after tests pass:

   git add tests/test_news_reliability_fp022.py scripts/test_news_reliability.sh

5. Commit only after the tests pass and the diff is reviewed. This milestone
   contains no production-code change and does not require a deployment.

SECURITY
--------
This bundle contains no credentials, secret configuration, .git metadata,
cache directories, or nested project copies.
