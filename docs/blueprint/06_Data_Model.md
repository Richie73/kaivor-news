# Kaivor Data Model

**Version:** 1.0

---

# Purpose

This document defines the core data entities used throughout Kaivor and the relationships between them.

A consistent data model reduces duplication, simplifies development, and supports future expansion.

---

# Design Principles

The data model should be:

- Consistent
- Extensible
- Normalised where practical
- Human-readable
- Versionable
- Backwards compatible where possible

---

# Core Entities

## User

Represents the owner of the Kaivor instance.

Examples of stored information:

- Preferences
- Settings
- Profiles
- Permissions

---

## Project

Represents a collection of related work.

Typical attributes:

- ID
- Name
- Description
- Status
- Tags
- Creation date
- Last modified

---

## Task

Represents a unit of work.

Typical attributes:

- ID
- Title
- Description
- Priority
- Due date
- Status
- Linked project
- Tags

---

## Note

Represents user-created information.

Typical attributes:

- ID
- Title
- Content
- Tags
- Linked entities
- Creation date

---

## Memory

Represents information Kaivor intentionally retains.

Examples:

- Preferences
- Long-term facts
- Conversation summaries
- Important decisions

Each memory should include:

- Importance
- Source
- Timestamp
- Confidence (where appropriate)

---

## Knowledge Item

Represents indexed information.

Examples:

- Documents
- PDFs
- Markdown
- Web content
- Technical references

---

## Plugin

Represents an installed extension.

Typical attributes:

- Name
- Version
- Author
- Capabilities
- Status

---

## Automation

Represents a workflow or scheduled action.

Examples:

- Reminder
- Daily briefing
- File processing
- Event trigger

---

# Relationships

Examples:

User

↓

Projects

↓

Tasks

↓

Notes

↓

Knowledge

↓

Memory

Automation may interact with any of the above.

Plugins may extend any module through approved interfaces.

---

# Identifiers

Every persistent entity should have a unique identifier.

Identifiers should remain stable.

---

# Metadata

Most entities should support:

- Created date
- Modified date
- Tags
- Version
- Source
- Status

---

# Storage Independence

The data model should remain independent of the storage implementation.

Whether data is stored in JSON, SQLite or another database should not change the structure of the model.

---

# Future Expansion

Future entities may include:

- Contacts
- Companies
- Assets
- Vehicles
- Locations
- Inventory
- Meetings
- Finance Records
- Learning Records

These should integrate with the existing model rather than introducing duplicate concepts.

---

# Guiding Principle

Model real-world concepts clearly.

Avoid creating multiple entities that represent the same idea.