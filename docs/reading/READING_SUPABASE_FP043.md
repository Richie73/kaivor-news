# Kaivor Reading — FP043 Supabase storage

## Purpose

FP043 adds a PostgreSQL repository adapter for the existing `reading/` domain.
The existing SQLite repository remains the default for local development and
tests. Production switches to PostgreSQL only when the explicit environment
variable `KAIVOR_READING_DATABASE_URL` is configured.

No Supabase credentials are stored in source code. The browser never connects
directly to Supabase. The Render server connects using a PostgreSQL connection
URI held as a private environment variable.

## Supabase setup

1. Open the existing `KaivorDatabase` project.
2. Confirm its status is Healthy.
3. Open SQL Editor and run the complete file:
   `migrations/reading/001_reading_schema.sql`
4. Confirm the five `reading_*` tables appear in the `public` schema.
5. In Project Settings / Connect, choose the **Transaction pooler** connection
   string (port 6543) for the application server. Use the URI form, not the
   Supabase project HTTPS URL and not the anon/public API key.
6. Keep the database password private. If the password is unknown, reset it in
   Supabase database settings and update any other application using it.

The adapter disables prepared statements for compatibility with PgBouncer
transaction pooling. TLS is required by the Supabase connection string; ensure
the URI includes `sslmode=require` if Supabase's copied URI does not already
include it.

## Render setup

After the FP043 code is deployed, open Render > kaivor-news > Environment and
set:

- `KAIVOR_READING_DATABASE_URL`: full Supabase transaction-pooler URI.
- `KAIVOR_READING_PIN`: a unique passphrase of at least 8 characters.
- `KAIVOR_SESSION_SECRET`: generate once using
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `KAIVOR_COOKIE_SECURE`: `true` (the Render service is HTTPS).
- `KAIVOR_READING_REQUIRE_POSTGRES`: `true` (declared in render.yaml; fail closed if the DB URL is missing).

The `render.yaml` declares these variables as unsynchronised secrets, except
`KAIVOR_COOKIE_SECURE`. Do not commit actual values, paste them into chat, or
put them in the ZIP.

The app does not run schema migrations automatically. This prevents a web
process from silently changing the database schema at startup.

## Data behaviour

- With `KAIVOR_READING_DATABASE_URL` set, Reading uses Supabase PostgreSQL.
- Without it, Reading uses the existing local SQLite database path
  (`KAIVOR_READING_DB_PATH`, otherwise `data/reading.db`).
- The migration is additive and creates only five `public.reading_*` tables.
- RLS is enabled on those tables. No anon/authenticated policies are created.
  The server-side PostgreSQL connection is private and must never be exposed
  to browser JavaScript.
- Existing SQLite records are not automatically copied. If any local books,
  notes or lists have been entered, keep the SQLite file and request a
  separately tested import before switching the live service.

## Validation

From the project root:

```bash
python -m pip install -r requirements.txt
python -m compileall -q reading reading_web.py
python -m pytest -q tests/test_reading_foundation_fp041.py tests/test_reading_web_fp042.py tests/test_reading_postgres_fp043.py
```

A live database smoke test should be performed only after the migration and
Render environment variables are configured. Add one disposable test book,
verify it appears after a page reload, then delete it.

## Rollback

Remove `KAIVOR_READING_DATABASE_URL` from Render to return the app to SQLite.
Do not drop the Supabase tables during rollback. Keep the database URL secret.
