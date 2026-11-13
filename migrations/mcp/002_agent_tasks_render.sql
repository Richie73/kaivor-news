-- FP078: Render Postgres adaptation of FP059 (migrations/mcp/001_agent_tasks.sql).
-- FP059 was written for Supabase: one REVOKE line names roles that do
-- not exist on Render Postgres, so the original file errors there. This
-- file is identical except that line is dropped; everything else (table,
-- indexes, grants, RLS, policy) is unchanged.
--
-- Apply only to the intended Kaivor database (the existing Reading
-- Postgres) after provisioning kaivor_mcp. Safe to rerun: does not drop
-- tables or task data; replaces only this policy.
-- Never store role passwords in migrations or source control.
--
-- Provision the role first (run once, as the database owner):
--   CREATE ROLE kaivor_mcp LOGIN PASSWORD '<a strong password you pick>';
-- Then run this file as the database owner, e.g. from Termux:
--   psql "$KAIVOR_READING_EXTERNAL_URL" -f migrations/mcp/002_agent_tasks_render.sql
-- (KAIVOR_READING_EXTERNAL_URL is the External Database URL from the
-- Render dashboard for the Reading database. It stays on your phone.)

-- Check prerequisites BEFORE creating or changing any database objects.
-- This avoids leaving a newly-created table behind if role provisioning was skipped.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kaivor_mcp') THEN
        RAISE EXCEPTION 'Required role kaivor_mcp is missing. Provision the dedicated runtime role before applying this migration.';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.agent_tasks (
    task_id text PRIMARY KEY,
    assigned_to text NOT NULL,
    task_type text NOT NULL,
    status text NOT NULL CHECK (status IN ('awaiting_approval','pending','running','completed','failed')),
    task_json jsonb NOT NULL,
    result_json jsonb,
    error_code text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_status_created
    ON public.agent_tasks (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_created
    ON public.agent_tasks (created_at DESC);

-- Remove all inherited/public access and restrict the runtime login to
-- exactly the operations required by PostgresAgentTaskStore.
REVOKE ALL ON TABLE public.agent_tasks FROM PUBLIC;
REVOKE ALL ON TABLE public.agent_tasks FROM kaivor_mcp;
REVOKE CREATE ON SCHEMA public FROM kaivor_mcp;
GRANT USAGE ON SCHEMA public TO kaivor_mcp;
GRANT SELECT, INSERT, UPDATE ON TABLE public.agent_tasks TO kaivor_mcp;

-- RLS is part of the migration, not a manual post-migration step. The runtime
-- role can access rows in this dedicated task table only; SQL privileges still
-- deny DELETE, TRUNCATE, REFERENCES and TRIGGER.
ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS kaivor_mcp_task_access ON public.agent_tasks;
CREATE POLICY kaivor_mcp_task_access
    ON public.agent_tasks
    FOR ALL
    TO kaivor_mcp
    USING (true)
    WITH CHECK (true);
