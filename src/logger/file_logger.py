"""File logger for JSON structured logging - compatible with Promtail/Loki."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class FileLogger:
    """Handles writing logs to JSON files by date."""

    def __init__(self, service_name: str, log_dir: str):
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self._file: Optional[Any] = None
        self._lock = threading.Lock()
        self._current_date: Optional[str] = None

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Open initial log file
        self._open_log_file()

        # Start daily rotation in background
        self._start_rotation_thread()

    def _open_log_file(self) -> None:
        """Open or create log file for today."""
        today = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            # Close existing file if date changed
            if self._file is not None and self._current_date != today:
                self._file.close()
                self._file = None

            if self._file is None:
                filename = self.log_dir / f"{today}-{self.service_name}.json"
                self._file = open(filename, "a", encoding="utf-8")
                self._current_date = today

    def _start_rotation_thread(self) -> None:
        """Start background thread for daily log rotation."""

        def rotate():
            import time

            while True:
                time.sleep(3600)  # Check every hour
                current_date = datetime.now().strftime("%Y-%m-%d")
                if current_date != self._current_date:
                    self._open_log_file()

        thread = threading.Thread(target=rotate, daemon=True)
        thread.start()

    def write_trace(self, data: dict) -> None:
        """Write a trace log entry."""
        # Add timestamp and service name
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "service_name": self.service_name,
            **data,
        }

        json_line = json.dumps(log_entry, ensure_ascii=False, default=str)

        with self._lock:
            if self._file is not None:
                self._file.write(json_line + "\n")
                self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


# Global logger instance
_global_logger: Optional[FileLogger] = None
_logger_lock = threading.Lock()


def init_file_logger(service_name: str, log_dir: str) -> FileLogger:
    """Initialize the global file logger."""
    global _global_logger

    with _logger_lock:
        if _global_logger is None:
            _global_logger = FileLogger(service_name, log_dir)

    return _global_logger


def get_file_logger() -> Optional[FileLogger]:
    """Get the global file logger instance."""
    return _global_logger
