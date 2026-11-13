"""Shared PIN + signed-session gate for Kaivor's private features.

One gate, used by the Reading blueprint and by the news app's mutating API
routes (FP069). The PIN (KAIVOR_READING_PIN, 8+ characters) and the Flask
session secret (KAIVOR_SESSION_SECRET, 32+ characters) must both be
configured, and the browser session must hold the authenticated flag set by
the Reading unlock flow (POST /reading/login). Until both hold, private
actions are locked with a clear message — never silently refused.
"""
from __future__ import annotations

import hmac
import os

from flask import jsonify, session

PIN_ENV_VAR = "KAIVOR_READING_PIN"
SESSION_SECRET_ENV_VAR = "KAIVOR_SESSION_SECRET"
SESSION_KEY = "reading_authenticated"
MIN_PIN_LENGTH = 8
MIN_SESSION_SECRET_LENGTH = 32


def configured_pin() -> str:
    return os.environ.get(PIN_ENV_VAR, "").strip()


def security_is_configured() -> bool:
    session_secret = os.environ.get(SESSION_SECRET_ENV_VAR, "")
    return len(configured_pin()) >= MIN_PIN_LENGTH and len(session_secret) >= MIN_SESSION_SECRET_LENGTH


def is_authenticated_session() -> bool:
    return bool(session.get(SESSION_KEY))


def pin_matches(supplied: str) -> bool:
    return hmac.compare_digest(supplied.encode("utf-8"), configured_pin().encode("utf-8"))


def mark_authenticated() -> None:
    session.clear()
    session[SESSION_KEY] = True
    session.permanent = True


def check_mutation_access():
    """Gate for the news app's mutating API routes (FP069).

    Returns None when the mutation may proceed, else a JSON error response:
    503 when the PIN/secret are not configured, 401 when the session has
    not been unlocked. The messages name the fix (configure, then unlock
    via the Reading section) so a locked app never fails silently.
    """
    if not security_is_configured():
        return jsonify({
            "success": False,
            "error": (
                "News settings are locked until KAIVOR_READING_PIN "
                "(8+ characters) and KAIVOR_SESSION_SECRET (32+ characters) "
                "are configured. Set them in the environment, restart the "
                "app, then unlock via the Reading section."
            ),
        }), 503
    if not is_authenticated_session():
        return jsonify({
            "success": False,
            "error": (
                "News settings need an unlocked session. "
                "Please unlock via the Reading section first (same PIN)."
            ),
        }), 401
    return None
