"""
PrivacyGuard - Logger
Writes timestamped events to logs/privacy_log.txt
"""

import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "privacy_log.txt")


class Logger:
    def __init__(self):
        self._path = os.path.abspath(LOG_PATH)
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def _write(self, level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}\n"
        print(line, end="")  # also print to console
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def info(self, message: str):
        self._write("INFO", message)

    def warn(self, message: str):
        self._write("WARN", message)

    def error(self, message: str):
        self._write("ERROR", message)

    def event(self, message: str):
        """High-level privacy events (triggers, deactivations)."""
        self._write("EVENT", message)

    def read_recent(self, n: int = 50) -> list[str]:
        """Return last n lines from log file."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [l.rstrip() for l in lines[-n:]]
        except Exception:
            return []
