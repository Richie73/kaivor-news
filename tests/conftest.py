"""Shared fixtures for Kaivor News tests.

FP069: `authed_client` configures the shared PIN + signed-session gate and
returns a test client holding an unlocked session, for tests that exercise
the news app's mutating API routes through HTTP.
"""
import pytest

import main

TEST_PIN = "test-pin-1234"
TEST_SESSION_SECRET = "s" * 32


@pytest.fixture
def authed_client(monkeypatch):
    """Test client with the FP069 gate configured and the session unlocked."""
    monkeypatch.setenv("KAIVOR_READING_PIN", TEST_PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", TEST_SESSION_SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client
