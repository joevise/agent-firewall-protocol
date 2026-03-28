"""AFP Event Logger — ring buffer + optional file logging."""
from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class AFPEvent:
    timestamp: str
    action: str
    target: str
    allowed: bool
    rule_id: str | None = None
    rule_name: str | None = None
    reason: str | None = None
    severity: str | None = None


class AFPLogger:
    def __init__(self, max_events: int = 1000, log_file: str | None = None):
        self._events: deque[AFPEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._log_file = log_file
        self._total = 0
        self._blocked = 0
        self._allowed = 0
        self._by_rule: dict[str, int] = {}

    def log(self, event: AFPEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._total += 1
            if event.allowed:
                self._allowed += 1
            else:
                self._blocked += 1
            if event.rule_id:
                self._by_rule[event.rule_id] = self._by_rule.get(event.rule_id, 0) + 1

        if self._log_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(asdict(event)) + "\n")
            except Exception:
                pass

    def get_events(self, limit: int = 100) -> list[dict]:
        with self._lock:
            evts = list(self._events)[-limit:]
        return [asdict(e) for e in reversed(evts)]

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total": self._total,
                "blocked": self._blocked,
                "allowed": self._allowed,
                "by_rule": dict(self._by_rule),
            }

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()
