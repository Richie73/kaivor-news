# Kaivor Project Structure

**Version:** 1.0

---

# Purpose

This document defines the canonical directory structure for Kaivor.

Every new module, package, document and asset should fit into this structure unless there is a strong architectural reason not to.

---

# Top-Level Structure

```
Kaivor/
├── core/
├── interfaces/
├── plugins/
├── docs/
├── tests/
├── config/
├── data/
├── scripts/
├── assets/
├── logs/
├── workspace/
└── main.py
```

---

# Directory Responsibilities

## core/

Contains the Kaivor engine.

Examples:

- AI
- Memory
- Knowledge
- Services
- Bootstrap
- Tasks
- Projects

The core contains business logic.

---

## interfaces/

Contains user interfaces.

Examples:

- CLI
- Android
- REST API
- Voice
- Web

Interfaces should remain lightweight.

---

## plugins/

Contains optional extensions.

Each plugin should be isolated from the core wherever practical.

---

## docs/

Project documentation.

Suggested layout:

```
docs/
├── blueprint/
├── architecture/
├── business/
├── construction/
├── knowledge/
├── projects/
├── quick-reference/
├── technology/
├── tools/
└── vehicles/
```

---

## tests/

Contains automated tests.

Examples:

- Unit tests
- Integration tests
- Regression tests

---

## config/

Configuration files.

Examples:

- YAML
- JSON
- TOML
- Environment templates

---

## data/

Persistent application data.

Examples:

- Databases
- JSON storage
- Cached indexes

---

## scripts/

Utility scripts.

Examples:

- Build scripts
- Migration scripts
- Maintenance tools

---

## assets/

Static resources.

Examples:

- Icons
- Images
- Fonts
- Templates

---

## logs/

Application log files.

Logs should never be committed to source control.

---

## workspace/

Temporary working data created while Kaivor is running.

This directory may be safely cleared if required.

---

# Naming Conventions

Directories:

- lowercase
- singular where appropriate
- descriptive names

Files:

- snake_case.py for Python
- PascalCase only where required by external tools
- Markdown documents in Title_Case.md

---

# Architectural Rules

- Keep modules focused.
- Avoid circular dependencies.
- Keep interfaces separate from business logic.
- Keep plugins isolated.
- Keep documentation up to date.

---

# Future Growth

This structure should comfortably support:

- Android application
- Local AI models
- Cloud providers
- Plugin ecosystem
- Multiple interfaces
- Automated testing
- Continuous integration

without major reorganisation.