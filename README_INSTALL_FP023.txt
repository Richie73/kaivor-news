Kaivor News FP023.0 — Subscription Reader

Purpose
- Detect article links belonging to The New York Times, The Telegraph, The Independent and The Athletic.
- Provide a publisher-labelled link that opens the original article in the user's browser.
- Allow the user to paste article text they are permitted to use and request a summary through Kaivor's existing AI brief endpoint.
- Does not scrape publisher sites, bypass logins/paywalls, or store pasted text in the news cache.

Files in this bundle
- main.py (complete replacement)
- templates/index.html (complete replacement)
- publisher_access.py (new)
- tests/test_publisher_access_fp023.py (new)

Installation (Termux)
1. From ~/Kaivor, extract this ZIP over the project root, preserving folder structure.
2. Run: python -m py_compile main.py publisher_access.py
3. Run: pytest -q tests
4. Run: git diff --check

Before installing
- Keep a separate backup of main.py and templates/index.html.
- Review changes and do not commit unrelated files.
- Pasted article text is sent to the AI provider configured by Kaivor when Generate summary is clicked. Only use text when your subscription and applicable terms permit that processing.
- Browser links use the publisher URL already present in the article; the user's normal subscription login is handled by the publisher website.

Changelog
FP023.0
- Added publisher URL detection using exact domain/subdomain matching.
- Added subscription-reader links for supported publishers in initial and saved article cards.
- Added opt-in pasted-text summary workflow using existing /api/ai_brief endpoint.
- No publisher scraping, session-cookie access, or paywall circumvention added.
