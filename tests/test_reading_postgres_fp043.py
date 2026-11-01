"""FP043 tests for the Supabase PostgreSQL Reading adapter selection."""
from pathlib import Path

import pytest
from flask import Flask

import reading_web
from reading.postgres_repository import PostgresReadingRepository


def test_postgres_repository_requires_a_postgresql_url():
    with pytest.raises(ValueError):
        PostgresReadingRepository("")
    with pytest.raises(ValueError):
        PostgresReadingRepository("https://example.supabase.co")


def test_postgres_repository_accepts_supabase_connection_uri():
    repository = PostgresReadingRepository(
        "postgresql://postgres.example:secret@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
    )
    assert repository.database_url.startswith("postgresql://")


def test_service_uses_postgres_when_explicit_database_url_is_configured(monkeypatch):
    captured = {}

    class FakePostgresRepository:
        def __init__(self, database_url):
            captured["url"] = database_url

    monkeypatch.setattr(reading_web, "PostgresReadingRepository", FakePostgresRepository)
    monkeypatch.setenv("KAIVOR_READING_DATABASE_URL", "postgresql://private-test-url")
    app = Flask(__name__)
    with app.app_context():
        service = reading_web._service()

    assert captured["url"] == "postgresql://private-test-url"
    assert isinstance(service.repository, FakePostgresRepository)


def test_service_keeps_sqlite_when_postgres_url_is_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
    app = Flask(__name__)
    app.config["READING_DB_PATH"] = str(tmp_path / "local-reading.db")
    with app.app_context():
        service = reading_web._service()

    assert service.repository.db_path == Path(app.config["READING_DB_PATH"])


def test_migration_is_additive_and_enables_rls():
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "reading"
        / "001_reading_schema.sql"
    ).read_text(encoding="utf-8")

    for table in (
        "reading_books",
        "reading_notes",
        "reading_progress",
        "reading_lists",
        "reading_list_items",
    ):
        assert f"CREATE TABLE IF NOT EXISTS public.{table}" in migration
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in migration

    assert "DROP TABLE" not in migration.upper()
    assert "auth." not in migration


def test_hosted_configuration_fails_closed_without_postgres_url(monkeypatch):
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
    monkeypatch.setenv("KAIVOR_READING_REQUIRE_POSTGRES", "true")
    app = Flask(__name__)
    with app.app_context():
        with pytest.raises(RuntimeError, match="Hosted Reading storage is not configured"):
            reading_web._service()
