"""Isolated child-process entry point for a bounded Kaivor News refresh."""
from __future__ import annotations

import contextlib
import json
import sys


def main() -> int:
    try:
        import main as kaivor_news

        # Keep machine-readable JSON on stdout; stage diagnostics go to stderr
        # and remain visible in Render's runtime logs.
        with contextlib.redirect_stdout(sys.stderr):
            articles = kaivor_news.fetch_fresh_news()
        sys.stdout.write(json.dumps(articles, ensure_ascii=False, separators=(",", ":")))
        sys.stdout.flush()
        return 0
    except Exception as exc:
        print(f"REFRESH CHILD: ERROR {type(exc).__name__}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
