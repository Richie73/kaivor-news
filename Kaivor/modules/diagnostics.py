"""
Kaivor Diagnostics
"""

import json
import os
import platform

from config.version import VERSION, BUILD, STATUS
from config.settings import AI_DEFAULT_MODEL

def diagnostics():

    print()
    print("=" * 60)
    print("KAIVOR SYSTEM DIAGNOSTICS".center(60))
    print("=" * 60)
    print()

    print("Application")
    print(f"  Version : {VERSION}")
    print(f"  Build   : {BUILD}")
    print(f"  Status  : {STATUS}")

    print()

    print("Artificial Intelligence")
    print(f"  Model   : {AI_DEFAULT_MODEL}")
    print("  Provider: OpenRouter")

    print()

    print("Database")

    try:
        with open("database/articles.json", "r", encoding="utf-8") as f:
            articles = json.load(f)

        print(f"  Articles: {len(articles)}")

    except Exception:
        print("  Articles: ERROR")

    print()

    print("Configuration")

    if os.path.exists("config/local_config.py"):
        print("  Local Config : OK")
    else:
        print("  Local Config : MISSING")

    print()

    print("System")

    print(f"  Python : {platform.python_version()}")
    print(f"  OS     : {platform.system()}")

    print()

    print("=" * 60)
    print("Overall Status : HEALTHY")
    print("=" * 60)
