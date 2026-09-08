## Version 0.9.64 — FP009 OpenRouter Provider Integration
- Implemented OpenRouter generation using the shared `AIRequest` interface.
- Added configurable OpenRouter model selection with `openrouter/auto` as the default.
- Added OpenRouter HTTP and configuration error handling.
- Fixed AI engine provider selection bookkeeping so failover and usage logging identify the provider that actually succeeded.
- Preserved the existing provider-independent architecture.

# Changelog

All notable changes to Kaivor are documented here.

## Version 0.9.62 - FP007 OpenAI-Compatible API

### Added
- Lightweight OpenAI-compatible API gateway for external AI interfaces.
- `/v1/models` and `/v1/chat/completions` endpoints.
- Optional API-key authentication via `KAIVOR_API_KEY`.
- Open WebUI integration documentation.
- API adapter tests.

### Architecture
- Open WebUI is treated as a UI/client layer; Kaivor remains the AI engine and provider-routing layer.

---

## Version 0.3.2 - Initial Git Release

### Added
- Multi-source RSS aggregation
- Feed Manager
- News Engine
- AI Intelligence module
- UK News
- World News
- Technology News
- Investment Research
- Football News
- Android News
- Music News
- Persistent article database
- Search engine
- Morning Dashboard
- Git repository support

### Fixed
- RSS date sorting across mixed time zones
- Duplicate article detection
- Feed loading improvements

---

## Version 0.2

### Added
- Article model
- RSS reader
- Modular project structure

---

## Version 0.1

### Initial release
- Project created
- Main menu
- Dashboard
- AI news module
