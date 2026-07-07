
"""
Kaivor Log Manager
"""

from pathlib import Path

from modules.developer.ui import (
    title,
    success,
    warning,
    error,
    start_timer,
    end_timer,
)

LOG_FILE = Path("logs/kaivor.log")


def view_log():

    start_timer()

    title("KAIVOR LOG")

    try:

        if LOG_FILE.exists():

            print(LOG_FILE.read_text(encoding="utf-8"))

        else:

            warning("No log file found.")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()


def clear_log():

    start_timer()

    title("CLEAR LOG")

    try:

        if not LOG_FILE.exists():

            warning("No log file found.")

        else:

            confirm = input("Clear log file? (y/N): ").strip().lower()

            if confirm == "y":

                LOG_FILE.write_text("", encoding="utf-8")

                success("Log file cleared.")

            else:

                warning("Cancelled.")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()