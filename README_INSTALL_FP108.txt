FP108 install — route the AI callers through the provider layer
====================================================================

DO NOT INSTALL until FP106 and FP107 are pushed. FP108 touches
main.py (FP106's file) and three FP107 provider files.

Files in this bundle (15):
  core/ai/request.py
  config/providers.json
  main.py
  rams_drafter.py
  receipt_reader.py
  core/providers/openrouter.py
  core/providers/openai.py
  core/providers/deepseek.py
  tests/test_provider_wiring_fp108.py
  tests/test_provider_layer_fp107.py
  tests/test_rams_drafting_fp100.py
  tests/test_receipt_capture_fp102.py
  CHANGELOG_FP108.txt
  README_INSTALL_FP108.txt
  BUNDLE_MANIFEST_FP108.txt

Install (from the Kaivor directory in Termux):

  cd ~/Kaivor
  cp core/ai/request.py core/ai/request.py.before-fp108
  cp config/providers.json config/providers.json.before-fp108
  cp main.py main.py.before-fp108
  cp rams_drafter.py rams_drafter.py.before-fp108
  cp receipt_reader.py receipt_reader.py.before-fp108
  cp core/providers/openrouter.py core/providers/openrouter.py.before-fp108
  cp core/providers/openai.py core/providers/openai.py.before-fp108
  cp core/providers/deepseek.py core/providers/deepseek.py.before-fp108
  # copy the new/changed files into place (Muse installs via SSH)

Test:

  python -m pytest tests/test_provider_wiring_fp108.py tests/test_provider_layer_fp107.py tests/test_chat_hub_fp077.py tests/test_rams_drafting_fp100.py tests/test_receipt_capture_fp102.py -q
  # expected: 57 passed

  python -m pytest tests/ -q
  # expected: 839 passed, 0 failed, 2 skipped

Push (after the phone suite is green):

  git add core/ai/request.py config/providers.json main.py rams_drafter.py receipt_reader.py core/providers/openrouter.py core/providers/openai.py core/providers/deepseek.py tests/test_provider_wiring_fp108.py tests/test_provider_layer_fp107.py tests/test_rams_drafting_fp100.py tests/test_receipt_capture_fp102.py CHANGELOG_FP108.txt README_INSTALL_FP108.txt BUNDLE_MANIFEST_FP108.txt
  git commit -m "FP108: route the AI callers through the provider layer"
  git push

Live check after deploy: send one chat message (locked route,
so verify on the phone), and confirm the intelligence drawer
still returns an analysis.
