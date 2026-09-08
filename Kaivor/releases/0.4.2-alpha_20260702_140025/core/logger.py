"""
Kaivor Performance Logger
"""

from datetime import datetime
from pathlib import Path
import time

LOG_FILE = Path("logs/kaivor.log")


class Logger:

    @staticmethod
    def _write(level, message):

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(LOG_FILE, "a", encoding="utf-8") as log:

            log.write("=" * 60 + "\n")
            log.write(f"{timestamp}\n")
            log.write(f"LEVEL : {level}\n")
            log.write(f"{message}\n\n")

    @staticmethod
    def info(message):
        Logger._write("INFO", message)

    @staticmethod
    def warning(message):
        Logger._write("WARNING", message)

    @staticmethod
    def error(message):
        Logger._write("ERROR", message)


class Timer:

    def __init__(self, task):

        self.task = task
        self.start = time.perf_counter()

    def stop(self):

        elapsed = time.perf_counter() - self.start

        Logger.info(
            f"""TASK : {self.task}
DURATION : {elapsed:.2f} seconds"""
        )

        return elapsed
