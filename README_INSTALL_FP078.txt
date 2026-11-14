KAIVOR FP078 — LINK MUSE TO KAIVOR
==================================

PURPOSE
-------
Puts Kaivor's link server (MCP) live on Render as a second service
next to the news app, so Muse can search Kaivor's knowledge and
send it research tasks. Read-only: Muse cannot change anything in
Kaivor or make it do things in the outside world.

This is a bigger job than the last few milestones because three
things have to happen outside the code: the database needs one new
table, the new service needs its secrets, and Muse needs the
connection set up. Everything is below in order. Nothing here needs
doing in a rush — do it when you have ten quiet minutes.

IMPORTANT NOTES
---------------
1. The OpenRouter key in the Render dashboard is the one that was
   exposed in the old snapshots (FP069). It was purged from the
   files but never revoked. Before this new service uses it, rotate
   it: make a new key at openrouter.ai, put the new key in the
   dashboard for BOTH services (kaivor-news and kaivor-mcp), then
   delete the old key at OpenRouter. Steps 2–4 below cover it.
2. No key, token or password goes in chat, in a file, or in the
   connector docs. You make them, you paste them into the
   dashboard, Muse never sees them.
3. The new service shares the existing Reading database. No new
   database, no new cost. The migration adds one table
   (agent_tasks) and the service connects as a limited user that
   can only use that one table.
4. Knowledge search starts switched off (no memory categories
   allowlisted) and the memory store on Render starts empty, so
   search will return nothing at first. The task tools work from
   day one.

FILES
-----
Replacement (back up the old copy as *.before-fp078 first):
- render.yaml (adds the kaivor-mcp service; kaivor-news untouched)

New:
- migrations/mcp/002_agent_tasks_render.sql
- tests/test_mcp_deploy_fp078.py
- CHANGELOG_FP078.txt
- README_INSTALL_FP078.txt
- BUNDLE_MANIFEST_FP078.txt

INSTALL (Termux)
----------------
The files are installed over SSH by Muse. The checks after install:

1. Targeted tests:
   cd ~/Kaivor
   python -m pytest tests/test_mcp_deploy_fp078.py -q
   Expect: 5 passed.

2. Full suite:
   python -m pytest -q
   Expect: 502 passed, 0 failed, 2 skipped (497 + 5 new).

PUSH
----
   cd ~/Kaivor
   git add render.yaml migrations/mcp/002_agent_tasks_render.sql tests/test_mcp_deploy_fp078.py CHANGELOG_FP078.txt README_INSTALL_FP078.txt BUNDLE_MANIFEST_FP078.txt
   git status --short
   git commit -m "FP078: deploy the MCP server for the Muse link"
   git push

Then commit the MCP server code itself. It was written earlier
(FP050–FP065) but never pushed, so Render cannot see it — the first
kaivor-mcp deploy failed on the missing requirements-mcp.txt.
These files live on the phone already; they just need committing:

   git add run_mcp.py requirements-mcp.txt requirements-postgres.txt core/integrations/__init__.py core/integrations/mcp_gateway.py core/integrations/mcp_observability.py core/integrations/mcp_runtime.py core/integrations/mcp_security.py core/agents/postgres_store.py migrations/mcp/001_agent_tasks.sql
   git commit -m "FP078: commit the MCP server code (was never pushed)"
   git push

(Note: core/agents/postgres_store.py is imported lazily by the
gateway at startup, so the service crashes without it. The MCP
tests and scripts/mcp_preflight.py stay uncommitted — Render does
not need them.)

Pushing does NOT create the new service by itself. The steps below
do that.

STEP 1 — MAKE THE TWO SECRETS (Termux)
--------------------------------------
Paste this into Termux. It prints two long random codes — the first
is the link token, the second is the database password for the
limited user. Write both down somewhere safe (your password
manager). Do NOT send them to Muse.

   python3 -c "import secrets; print('LINK TOKEN: ' + secrets.token_hex(24)); print('DB PASSWORD: ' + secrets.token_hex(24))"

Each code is 48 characters with no spaces — that is what the server
wants.

STEP 2 — ROTATE THE OPENROUTER KEY
----------------------------------
1. Go to openrouter.ai and sign in. Go to Keys, create a new key,
   copy it.
2. In the Render dashboard, open kaivor-news, go to Environment,
   and replace the value of OPENROUTER_API_KEY with the new key.
   (The news app will redeploy — that is normal.)
3. Back at OpenRouter, delete the OLD key.
4. Keep the new key handy — Step 4 needs it again for kaivor-mcp.

STEP 3 — ADD THE DATABASE TABLE (Termux)
----------------------------------------
The Reading database lives on Supabase, NOT on Render — there is
no PostgreSQL database in the Render workspace. So use the
original Supabase migration (001), not the Render adaptation
(002), and use the database URL the news app already uses.

1. In the Render dashboard, open kaivor-news, go to Environment,
   find KAIVOR_READING_DATABASE_URL and reveal it. Copy the whole
   value (it starts with postgresql://).
2. In Termux, do it in three small pastes — pasting the whole
   block at once makes the first prompt swallow the next line.
   First paste just this line, then paste the database URL at the
   prompt and press Enter:

   read -p "Paste the database URL: " DBURL

   Then paste just this line, then paste the DB password from
   Step 1:

   read -s -p "Paste the DB password from Step 1: " DBPASS

   Then paste these two lines together:

   psql "$DBURL" -v ON_ERROR_STOP=1 -c "CREATE ROLE kaivor_mcp LOGIN PASSWORD '$DBPASS';"
   psql "$DBURL" -v ON_ERROR_STOP=1 -f migrations/mcp/001_agent_tasks.sql

   Expect: CREATE ROLE, then a list of CREATE TABLE / CREATE INDEX /
   REVOKE / GRANT / ALTER TABLE / CREATE POLICY lines, no errors.
   (A NOTICE that the policy does not exist is normal on a first
   run.) If it says the role already exists, that step is already
   done — just run the second psql line on its own.

STEP 4 — CREATE THE NEW SERVICE (Render dashboard)
--------------------------------------------------
There is no Blueprint for kaivor-news (it was created manually),
so create the service by hand:

1. In the Render dashboard tap + New -> Web Service and pick the
   kaivor-news repo (Richie73 / kaivor-news).
2. Name it kaivor-mcp, region Oregon, Free plan.
3. Build command:
   pip install -r requirements.txt -r requirements-mcp.txt -r requirements-postgres.txt
4. Start command:
   python run_mcp.py
5. Add these environment variables (one at a time, Key then Value):
   - PYTHON_VERSION = 3.11.9 (matches the news app; without it
     Render uses its default Python)
   - KAIVOR_MCP_ENV = production
   - KAIVOR_MCP_HOST = 0.0.0.0
   - KAIVOR_MCP_BEARER_TOKEN = the link token from Step 1
   - OPENROUTER_API_KEY = the new key from Step 2
   - KAIVOR_AGENT_DATABASE_URL = the database URL from Step 3,
     with two changes: the username becomes
     kaivor_mcp.<the same code after "postgres." in the URL>
     (the Supabase pooler needs the project code on the username)
     and the password becomes the DB password from Step 1.
     Everything else in the URL stays the same.
6. Tap Deploy Web Service. It may take a minute to build. The
   service URL will be https://kaivor-mcp.onrender.com
7. Tell Muse it is live. Muse will check the service answers
   (it should refuse requests without the token — that proves it
   is up and locked), then send you the secure link to connect
   Muse to it. You paste the link token into that secure page;
   Muse never sees it.
