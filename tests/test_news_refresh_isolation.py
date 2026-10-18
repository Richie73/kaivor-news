"""Regression tests for bounded, isolated news collection."""
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import pytest

import main


def test_isolated_fetch_parses_article_list():
    payload = '[{"title":"Example","category":"World"}]'
    with patch.object(
        main.subprocess,
        "run",
        return_value=CompletedProcess(args=["python"], returncode=0, stdout=payload),
    ) as run:
        result = main._fetch_fresh_news_isolated()

    assert result == [{"title": "Example", "category": "World"}]
    assert run.call_args.kwargs["timeout"] == 90
    assert run.call_args.kwargs["check"] is False
    assert run.call_args.kwargs["stdout"] == main.subprocess.PIPE


def test_isolated_fetch_rejects_child_failure():
    with patch.object(
        main.subprocess,
        "run",
        return_value=CompletedProcess(args=["python"], returncode=1, stdout=""),
    ):
        with pytest.raises(RuntimeError, match="exited with status 1"):
            main._fetch_fresh_news_isolated()


def test_isolated_fetch_rejects_invalid_json():
    with patch.object(
        main.subprocess,
        "run",
        return_value=CompletedProcess(args=["python"], returncode=0, stdout="not-json"),
    ):
        with pytest.raises(RuntimeError, match="invalid JSON"):
            main._fetch_fresh_news_isolated()


def test_isolated_fetch_propagates_hard_timeout():
    with patch.object(main.subprocess, "run", side_effect=TimeoutExpired(cmd="runner", timeout=90)):
        with pytest.raises(TimeoutExpired):
            main._fetch_fresh_news_isolated()


def test_refresh_news_accepts_fetcher_and_preserves_existing_cache():
    existing = [{"id": "existing-story", "title": "Existing"}]
    with main._news_lock:
        original_articles = main._news_cache["articles"]
        original_updated = main._news_cache["last_updated"]
        main._news_cache["articles"] = existing
        main._news_cache["last_updated"] = 12345.0

    try:
        result = main.refresh_news(fetcher=lambda: [])
        assert result == []
        with main._news_lock:
            assert main._news_cache["articles"] == existing
            assert main._news_cache["last_updated"] == 12345.0
    finally:
        with main._news_lock:
            main._news_cache["articles"] = original_articles
            main._news_cache["last_updated"] = original_updated
