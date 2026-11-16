FP107 install — one working provider layer
==============================================

Files in this bundle (9):
  core/providers/base.py
  core/providers/openrouter.py
  core/providers/openai.py
  core/providers/deepseek.py
  core/providers/manager.py
  tests/test_provider_layer_fp107.py
  CHANGELOG_FP107.txt
  README_INSTALL_FP107.txt
  BUNDLE_MANIFEST_FP107.txt

Install (from the Kaivor directory in Termux):

  cd ~/Kaivor
  cp core/providers/base.py core/providers/base.py.before-fp107
  cp core/providers/openrouter.py core/providers/openrouter.py.before-fp107
  cp core/providers/openai.py core/providers/openai.py.before-fp107
  cp core/providers/deepseek.py core/providers/deepseek.py.before-fp107
  cp core/providers/manager.py core/providers/manager.py.before-fp107
  # copy the new/changed files into place (Muse installs via SSH)

Test:

  python -m pytest tests/test_provider_layer_fp107.py -q
  # expected: 12 passed

  python -m pytest tests/ -q
  # expected: 831 passed, 0 failed, 2 skipped

Push (after the phone suite is green):

  git add core/providers/base.py core/providers/openrouter.py core/providers/openai.py core/providers/deepseek.py core/providers/manager.py tests/test_provider_layer_fp107.py CHANGELOG_FP107.txt README_INSTALL_FP107.txt BUNDLE_MANIFEST_FP107.txt
  git commit -m "FP107: one working provider layer"
  git push

No setup step: the layer reads the same env keys the live app
already uses. FP108 wires the callers to it.
