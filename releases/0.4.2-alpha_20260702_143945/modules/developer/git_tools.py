"""
Kaivor Git Tools
"""

import subprocess

from modules.developer.ui import (
    title,
    start_timer,
    end_timer,
    success,
    warning,
    error,
)


def git_status():

    start_timer()

    title("GIT STATUS")

    try:

        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout.strip()

        if output:
            print(output)
        else:
            success("Working tree clean.")

    except FileNotFoundError:
        error("Git is not installed.")

    except subprocess.CalledProcessError as e:
        error("Git command failed.")
        if e.stderr:
            print(e.stderr)

    finally:
        end_timer()