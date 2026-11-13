"""FP078: the Kaivor MCP service is deployable on Render.

String checks only — PyYAML is not installed in Termux, so these tests
must run on the phone without it. (The file is also validated as real
YAML by hand before shipping.)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_YAML = ROOT / "render.yaml"
MIGRATION = ROOT / "migrations" / "mcp" / "002_agent_tasks_render.sql"
MIGRATION_001 = ROOT / "migrations" / "mcp" / "001_agent_tasks.sql"


def _service_block(text, name):
    marker = f"name: {name}"
    start = text.index(marker)
    rest = text[start:]
    # The next service block starts at the following "  - type: web".
    nxt = rest.find("  - type: web", len(marker))
    return rest if nxt == -1 else rest[:nxt]


def test_render_yaml_declares_the_mcp_service():
    text = RENDER_YAML.read_text(encoding="utf-8")
    block = _service_block(text, "kaivor-mcp")
    assert "type: web" in text
    assert "startCommand: python run_mcp.py" in block
    assert "pip install -r requirements.txt -r requirements-mcp.txt -r requirements-postgres.txt" in block
    assert "KAIVOR_MCP_ENV" in block
    assert 'value: "production"' in block
    assert "KAIVOR_MCP_HOST" in block
    assert 'value: "0.0.0.0"' in block
    assert "KAIVOR_MCP_BEARER_TOKEN" in block
    assert "KAIVOR_AGENT_DATABASE_URL" in block
    assert "OPENROUTER_API_KEY" in block
    assert "KAIVOR_MCP_ALLOWED_MEMORY_CATEGORIES" in block
    # Secrets must be dashboard-managed, never in the file.
    assert block.count("sync: false") == 3
    # The MCP service exposes no health endpoint, so no healthCheckPath:
    # Render falls back to its port check.
    assert "healthCheckPath" not in block


def test_render_yaml_keeps_the_news_service_intact():
    text = RENDER_YAML.read_text(encoding="utf-8")
    block = _service_block(text, "kaivor-news")
    assert "startCommand: gunicorn main:app" in block
    assert "healthCheckPath: /api/health" in block
    assert "KAIVOR_READING_DATABASE_URL" in block


def test_render_migration_is_the_supabase_free_adaptation():
    sql = MIGRATION.read_text(encoding="utf-8")
    # Same objects as FP059.
    assert "CREATE TABLE IF NOT EXISTS public.agent_tasks" in sql
    assert "rolname = 'kaivor_mcp'" in sql
    assert "GRANT SELECT, INSERT, UPDATE ON TABLE public.agent_tasks TO kaivor_mcp" in sql
    assert "ALTER TABLE public.agent_tasks ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY kaivor_mcp_task_access" in sql
    # The Supabase-only roles are gone: they do not exist on Render
    # Postgres and the original REVOKE line errors there.
    assert "anon" not in sql
    assert "authenticated" not in sql
    assert "service_role" not in sql
    # No real password is stored in the file: the only PASSWORD literal
    # is the placeholder in the commented provisioning example.
    assert sql.count("PASSWORD '") == 1
    assert "'<a strong password you pick>'" in sql


def test_render_migration_matches_the_fp059_table():
    # The table definition must stay identical to FP059's, so the
    # PostgresAgentTaskStore works against either migration.
    sql_002 = MIGRATION.read_text(encoding="utf-8")
    sql_001 = MIGRATION_001.read_text(encoding="utf-8")

    def table_block(sql):
        start = sql.index("CREATE TABLE IF NOT EXISTS public.agent_tasks")
        return sql[start:sql.index(");", start) + 2]

    assert table_block(sql_002) == table_block(sql_001)


def test_mcp_entrypoint_exists():
    entry = (ROOT / "run_mcp.py").read_text(encoding="utf-8")
    assert "build_mcp_app" in entry
    assert "MCPRuntimeConfig.from_environment" in entry
