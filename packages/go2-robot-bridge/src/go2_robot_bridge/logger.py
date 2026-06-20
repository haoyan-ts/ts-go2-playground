"""Structured logger for Robot Bridge — JSON-lines event log."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class Logger:
    """Writes timestamped JSON-line events to a log file."""

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            log_path = Path("bridge_run.log")
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Write a single event as a JSON line."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload or {},
        }
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_action_start(self, action_name: str) -> None:
        self.log_event("action_start", {"action": action_name})

    def log_action_complete(self, action_name: str, duration_s: float) -> None:
        self.log_event(
            "action_complete",
            {
                "action": action_name,
                "duration_s": round(duration_s, 3),
            },
        )

    def log_action_error(self, action_name: str, error: str) -> None:
        self.log_event("action_error", {"action": action_name, "error": error})

    def log_step(self, step_type: str, result: Dict[str, Any]) -> None:
        self.log_event("step_executed", {"step_type": step_type, "result": result})

    def log_stop(self) -> None:
        self.log_event("stop_executed", {})

    @property
    def log_path(self) -> Path:
        return self._log_path
