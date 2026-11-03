KAIVOR FP049 — AGENT COLLABORATION FOUNDATION
=============================================

Purpose
-------
Introduce a provider-independent, permission-aware agent task foundation. This
milestone creates task contracts, an agent registry, SQLite task persistence,
explicit approval gates, a native Kaivor AI adapter and a CLI inspection command.
It does NOT connect to Meta Muse or perform external actions.

Files
-----
New: core/agents/__init__.py
New: core/agents/models.py
New: core/agents/base.py
New: core/agents/registry.py
New: core/agents/store.py
New: core/agents/orchestrator.py
New: core/agents/kaivor_ai.py
New: commands/agents.py
New: tests/test_agents_fp049.py
Replacement: kaivor.py

Install (Termux)
----------------
1. Copy Kaivor_FP049_Agent_Collaboration.zip to Android Downloads.
2. Run: cd ~/Kaivor && unzip -o ~/storage/shared/Download/Kaivor_FP049_Agent_Collaboration.zip -d ~/Kaivor
3. Compile: python -m py_compile core/agents/*.py commands/agents.py kaivor.py tests/test_agents_fp049.py
4. Test: python -m pytest -q tests/test_agents_fp049.py
5. Inspect: git status --short && git diff --check && git diff --stat
6. CLI check: python kaivor.py agents

Persistence
-----------
Tasks are stored in data/agent_tasks.db (SQLite). The database is runtime data and
is not included in this bundle. The store creates its table and index automatically.

Safety model
------------
- Read-only permissions are the default.
- Write, external-action and secret-access permissions require explicit approval.
- Tasks requiring approval remain awaiting_approval until an identified approver is supplied.
- The approval method is an internal foundation API; future web/connector adapters must
  authenticate the approver before calling it.
- Agent results must identify the assigned agent.
- Exception text is not persisted; only a stable error code is recorded.
- No agent receives credentials through the task contract.

Meta Muse status
----------------
No Meta credentials, connector endpoints or API calls are included. FP050 will only
be designed after the official Muse connector requirements and account availability
are verified.
