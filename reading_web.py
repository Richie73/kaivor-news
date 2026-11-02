"""Private Flask interface for the Kaivor News Reading module.

Reading records are personal data. The blueprint is locked behind a separately
configured PIN and signed Flask session; no BorrowBox credentials are collected.
"""
from __future__ import annotations

import hmac
import os
from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from reading.models import BOOK_FORMATS, READING_STATUSES
from reading.providers import BorrowBoxProvider
from reading.service import ReadingService, ReadingValidationError
from reading.postgres_repository import PostgresReadingRepository

reading_bp = Blueprint("reading", __name__)
MAX_TEXT = 4000
MAX_TITLE = 240
MAX_AUTHOR = 240


def _configured_pin() -> str:
    return os.environ.get("KAIVOR_READING_PIN", "").strip()


def _security_is_configured() -> bool:
    session_secret = os.environ.get("KAIVOR_SESSION_SECRET", "")
    return len(_configured_pin()) >= 8 and len(session_secret) >= 32


def _db_path() -> str:
    configured = current_app.config.get("READING_DB_PATH") or os.environ.get("KAIVOR_READING_DB_PATH")
    return str(configured or Path("data") / "reading.db")


def _service() -> ReadingService:
    # Hosted production uses Supabase PostgreSQL. Local development and tests
    # retain the existing SQLite repository unless the explicit URL is set.
    database_url = (
        current_app.config.get("READING_DATABASE_URL")
        or os.environ.get("KAIVOR_READING_DATABASE_URL", "").strip()
    )
    if database_url:
        repository = PostgresReadingRepository(database_url)
        return ReadingService(repository=repository)
    require_postgres = str(
        current_app.config.get("READING_REQUIRE_POSTGRES")
        or os.environ.get("KAIVOR_READING_REQUIRE_POSTGRES", "")
    ).strip().lower() in {"1", "true", "yes"}
    if require_postgres:
        raise RuntimeError(
            "Hosted Reading storage is not configured. Set KAIVOR_READING_DATABASE_URL "
            "to the private Supabase PostgreSQL transaction-pooler URI."
        )
    return ReadingService(db_path=_db_path())


def _json_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _book_dict(book):
    return asdict(book)


def _note_dict(note):
    return asdict(note)


def _progress_dict(progress):
    return asdict(progress)


def _clean_optional(value, limit=MAX_TEXT):
    if value is None:
        return None
    cleaned = str(value).strip()
    if len(cleaned) > limit:
        raise ReadingValidationError(f"Text fields must be {limit} characters or fewer.")
    return cleaned or None


@reading_bp.before_request
def _require_reading_access():
    # The page and login endpoint must remain reachable while locked.
    if request.endpoint in {"reading.reading_page", "reading.reading_login", "reading.reading_logout"}:
        return None
    if not _security_is_configured():
        return _json_error(
            "Reading is locked until KAIVOR_READING_PIN (8+ characters) and KAIVOR_SESSION_SECRET (32+ characters) are configured.",
            503,
        )
    if not session.get("reading_authenticated"):
        return _json_error("Reading session expired. Please unlock the Reading section.", 401)
    return None


@reading_bp.get("/reading")
def reading_page():
    configured = _security_is_configured()
    authenticated = bool(configured and session.get("reading_authenticated"))
    return render_template(
        "reading.html",
        pin_configured=configured,
        authenticated=authenticated,
        login_failed=request.args.get("error") == "1",
    )


@reading_bp.post("/reading/login")
def reading_login():
    expected = _configured_pin()
    supplied = str(request.form.get("pin") or "")
    if not _security_is_configured():
        return redirect(url_for("reading.reading_page"))
    if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
        return redirect(url_for("reading.reading_page", error="1"))
    session.clear()
    session["reading_authenticated"] = True
    session.permanent = True
    return redirect(url_for("reading.reading_page"))


@reading_bp.post("/reading/logout")
def reading_logout():
    session.clear()
    return redirect(url_for("reading.reading_page"))


@reading_bp.get("/api/reading/dashboard")
def reading_dashboard():
    service = _service()
    books = service.repository.list_books()
    summary = service.dashboard()
    latest = []
    for book in books:
        progress = service.repository.latest_progress(book.id)
        latest.append({
            "book": _book_dict(book),
            "progress": _progress_dict(progress) if progress else None,
            "notes_count": len(service.repository.list_notes(book.id)),
        })
    return jsonify({
        "success": True,
        "summary": summary,
        "books": latest,
        "statuses": list(READING_STATUSES),
        "formats": list(BOOK_FORMATS),
        "borrowbox": {
            "connected": False,
            "sync_available": False,
            "message": "Waiting for an authorised integration method from Bolinda.",
        },
    })


@reading_bp.route("/api/reading/books", methods=["GET", "POST"])
def reading_books():
    service = _service()
    if request.method == "GET":
        query = str(request.args.get("q") or "").strip()
        status = str(request.args.get("status") or "").strip()
        if status and status not in READING_STATUSES:
            return _json_error("Unsupported reading status.")
        books = service.repository.search_books(query) if query else service.repository.list_books()
        if status:
            books = [book for book in books if book.status == status]
        return jsonify({"success": True, "books": [_book_dict(book) for book in books]})

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    try:
        title = str(data.get("title") or "").strip()
        author = _clean_optional(data.get("author"), MAX_AUTHOR)
        description = _clean_optional(data.get("description"))
        book_format = str(data.get("book_format") or "other")
        status = str(data.get("status") or "want_to_read")
        if len(title) > MAX_TITLE:
            return _json_error(f"Book titles must be {MAX_TITLE} characters or fewer.")
        book = service.add_book(
            title=title,
            author=author,
            book_format=book_format,
            status=status,
            description=description,
            provider="manual",
        )
        return jsonify({"success": True, "book": _book_dict(book)}), 201
    except ReadingValidationError as exc:
        return _json_error(str(exc))
    except Exception as exc:
        # SQLite's unique provider identity constraint is not exposed as a traceback.
        import sqlite3
        if isinstance(exc, sqlite3.IntegrityError):
            return _json_error("That provider book already exists.")
        raise


@reading_bp.route("/api/reading/books/<int:book_id>", methods=["GET", "PATCH", "DELETE"])
def reading_book_detail(book_id: int):
    service = _service()
    book = service.repository.get_book(book_id)
    if not book:
        return _json_error("Book not found.", 404)

    if request.method == "GET":
        notes = service.repository.list_notes(book_id)
        progress = service.repository.latest_progress(book_id)
        return jsonify({
            "success": True,
            "book": _book_dict(book),
            "notes": [_note_dict(note) for note in notes],
            "progress": _progress_dict(progress) if progress else None,
        })

    if request.method == "DELETE":
        service.delete_book(book_id)
        return jsonify({"success": True, "deleted": True})

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    try:
        updates = {}
        if "title" in data:
            title = str(data.get("title") or "").strip()
            if not title or len(title) > MAX_TITLE:
                return _json_error(f"Title is required and must be {MAX_TITLE} characters or fewer.")
            updates["title"] = title
        if "author" in data:
            updates["author"] = _clean_optional(data.get("author"), MAX_AUTHOR)
        if "description" in data:
            updates["description"] = _clean_optional(data.get("description"))
        if "book_format" in data:
            value = str(data.get("book_format") or "")
            if value not in BOOK_FORMATS:
                return _json_error("Unsupported book format.")
            updates["book_format"] = value
        if "status" in data:
            service.update_status(book_id, str(data.get("status")))
        updated = service.repository.update_book(book_id, **updates) if updates else service.repository.get_book(book_id)
        return jsonify({"success": True, "book": _book_dict(updated)})
    except ReadingValidationError as exc:
        return _json_error(str(exc))


@reading_bp.route("/api/reading/books/<int:book_id>/notes", methods=["GET", "POST"])
def reading_book_notes(book_id: int):
    service = _service()
    if not service.repository.get_book(book_id):
        return _json_error("Book not found.", 404)
    if request.method == "GET":
        return jsonify({"success": True, "notes": [_note_dict(n) for n in service.repository.list_notes(book_id)]})
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    try:
        note = service.add_note(
            book_id,
            str(data.get("note") or ""),
            _clean_optional(data.get("page_reference"), 120),
        )
        return jsonify({"success": True, "note": _note_dict(note)}), 201
    except ReadingValidationError as exc:
        return _json_error(str(exc))


@reading_bp.get("/api/reading/books/<int:book_id>/progress")
def reading_book_progress_history(book_id: int):
    service = _service()
    if not service.repository.get_book(book_id):
        return _json_error("Book not found.", 404)
    return jsonify({"success": True, "progress": [_progress_dict(item) for item in service.repository.list_progress(book_id)]})


@reading_bp.post("/api/reading/books/<int:book_id>/progress")
def reading_book_progress(book_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    try:
        value = float(data.get("value"))
        unit = str(data.get("unit") or "percent")
        service = _service()
        progress = service.record_progress(book_id, value, unit)
        # Percentage progress provides an unambiguous status transition.
        # Non-percentage units never alter status because their total is unknown.
        if unit == "percent":
            if value >= 100:
                service.update_status(book_id, "finished")
            elif value > 0:
                book = service.repository.get_book(book_id)
                if book and book.status == "want_to_read":
                    service.update_status(book_id, "reading")
        return jsonify({"success": True, "progress": _progress_dict(progress)}), 201
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc) or "Progress value must be numeric.")


@reading_bp.route("/api/reading/lists", methods=["GET", "POST"])
def reading_lists():
    service = _service()
    if request.method == "GET":
        return jsonify({"success": True, "lists": service.repository.list_lists()})
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    name = str(data.get("name") or "").strip()
    description = _clean_optional(data.get("description"))
    if not name:
        return _json_error("List name is required.")
    if len(name) > 120:
        return _json_error("List names must be 120 characters or fewer.")
    try:
        list_id = service.repository.create_list(name, description)
        return jsonify({"success": True, "list": {"id": list_id, "name": name, "description": description}}), 201
    except Exception as exc:
        import sqlite3
        if isinstance(exc, sqlite3.IntegrityError):
            return _json_error("A reading list with that name already exists.")
        raise


@reading_bp.route("/api/reading/lists/<int:list_id>/books", methods=["GET", "POST"])
def reading_list_books(list_id: int):
    service = _service()
    known_lists = {item["id"] for item in service.repository.list_lists()}
    if list_id not in known_lists:
        return _json_error("Reading list not found.", 404)
    if request.method == "GET":
        return jsonify({"success": True, "books": [_book_dict(b) for b in service.repository.list_contents(list_id)]})
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("A JSON object is required.")
    try:
        book_id = int(data.get("book_id"))
        service.repository.add_to_list(list_id, book_id)
        return jsonify({"success": True, "added": True})
    except (TypeError, ValueError):
        return _json_error("A valid book_id is required.")
    except KeyError as exc:
        return _json_error(str(exc), 404)


@reading_bp.get("/api/reading/providers")
def reading_providers():
    provider = BorrowBoxProvider()
    return jsonify({
        "success": True,
        "providers": [{
            "name": provider.name,
            "launch_url": provider.get_launch_url(),
            "connected": False,
            "capabilities": {
                "catalog_search": provider.capabilities.catalog_search,
                "loans": provider.capabilities.loans,
                "due_dates": provider.capabilities.due_dates,
                "progress_sync": provider.capabilities.progress_sync,
            },
            "status": "awaiting_authorisation",
        }],
    })
