FP031 — AI Brief Validation and Fallback Hardening
=================================================

Bundle contents
---------------
- main.py
  Complete replacement for the current Kaivor News API entry point.
- tests/test_ai_brief_validation_fp031.py
  Regression tests for valid provider output, malformed provider payloads,
  invalid provider briefs, provider exceptions, HTTP errors, and invalid or
  failing deterministic fallbacks.
- README_INSTALL.txt
  Installation, rollback, compile, and test instructions.
- CHANGELOG.txt
  Milestone changes.

Install location
----------------
Install from Termux into the existing project root: ~/Kaivor

Do NOT extract this archive into ~/Kaivor/Kaivor. The archive paths are
relative to the project root and replace ~/Kaivor/main.py.

1. Download the ZIP to Android's Download folder.
2. In Termux, inspect the archive:
     unzip -l ~/storage/shared/Download/FP031-AI-Brief-Validation-Hardening.zip
3. Back up the current entry point:
     cd ~/Kaivor
     cp main.py main.py.fp030-backup
4. Extract the complete bundle into the project root:
     unzip -o ~/storage/shared/Download/FP031-AI-Brief-Validation-Hardening.zip -d ~/Kaivor
5. Compile:
     cd ~/Kaivor
     python -m py_compile main.py tests/test_ai_brief_validation_fp031.py
6. Run the FP030 validator unit tests and the FP031 integration tests:
     python -m pytest -q tests/test_brief_quality_validation_fp030.py tests/test_ai_brief_validation_fp031.py
7. Run the full regression suite:
     python -m pytest -q tests

The app's existing runtime/test dependencies must already be installed. If
collection reports a missing dependency, install the project's requirements
in the established Termux environment before interpreting the result:
     python -m pip install -r requirements.txt

What changes
------------
- Provider HTTP errors, request exceptions, malformed JSON/payload structures,
  and structurally invalid briefs receive distinct safe diagnostic reasons.
- A provider with invalid output is rejected and the next configured provider
  is tried.
- Successful provider responses include aggregate rejection diagnostics for
  earlier providers, without returning provider response bodies, article URLs,
  API keys, or exception details.
- Deterministic fallback output is validated before it is returned.
- If fallback generation fails or its result fails validation, the endpoint
  returns HTTP 502 with success=false and does not expose the invalid brief.
- Valid deterministic fallback behavior remains successful and includes
  validation diagnostics.

Rollback
--------
If tests fail or the app behaves unexpectedly:
     cd ~/Kaivor
     cp main.py.fp030-backup main.py
     python -m py_compile main.py

This bundle changes files only when you install it. It does not commit, push,
or deploy anything. Review and test before staging or deploying.
