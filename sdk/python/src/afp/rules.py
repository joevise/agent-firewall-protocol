from __future__ import annotations

import time
import threading
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .models import Rule
from .patterns import matches


def load_rules_from_yaml(path: str | Path) -> list[Rule]:
    """Load rules from a YAML file (multi-document)."""
    path = Path(path)
    rules: list[Rule] = []
    with open(path) as f:
        for doc in yaml.safe_load_all(f):
            if not doc or "rule" not in doc:
                continue
            r = doc["rule"]
            trigger = r.get("trigger", {})
            rules.append(Rule(
                id=r["id"],
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", ""),
                severity=r.get("severity", "medium"),
                trigger_actions=trigger.get("action_type", []),
                conditions=r.get("conditions", {}),
                action=r.get("action", "block"),
                message=r.get("message", ""),
            ))
    return rules


def load_rules_from_dir(directory: str | Path) -> list[Rule]:
    """Load all YAML rules from a directory."""
    d = Path(directory)
    rules: list[Rule] = []
    for p in sorted(d.glob("*.yaml")):
        rules.extend(load_rules_from_yaml(p))
    for p in sorted(d.glob("*.yml")):
        rules.extend(load_rules_from_yaml(p))
    return rules


class RuleEngine:
    """Evaluate conditions against rules."""

    def __init__(self, allowed_domains: list[str] | None = None):
        self.allowed_domains: set[str] = set(allowed_domains or [])
        self._request_log: list[float] = []
        self._lock = threading.Lock()

    # ── public ──

    def evaluate_conditions(self, conditions: dict, action: str, params: dict, context: dict) -> bool:
        """Return True if the conditions are met (rule should fire)."""
        return self._eval(conditions, action, params, context)

    # ── private ──

    def _eval(self, cond: dict, action: str, params: dict, ctx: dict) -> bool:
        if "all" in cond:
            return all(self._eval(c, action, params, ctx) if isinstance(c, dict) else self._eval_leaf(c, action, params, ctx) for c in cond["all"])
        if "any" in cond:
            return any(self._eval(c, action, params, ctx) if isinstance(c, dict) else self._eval_leaf(c, action, params, ctx) for c in cond["any"])
        # Single-condition dict
        for key in cond:
            if not self._eval_single(key, cond[key], action, params, ctx):
                return False
        return True

    def _eval_leaf(self, item, action: str, params: dict, ctx: dict) -> bool:
        if isinstance(item, dict):
            return self._eval(item, action, params, ctx)
        return False

    def _eval_single(self, key: str, value, action: str, params: dict, ctx: dict) -> bool:
        if key == "content_matches":
            text = self._extract_content(params)
            return matches(value, text)

        if key == "destination_not_in":
            url = params.get("url", "")
            domain = self._extract_domain(url)
            return domain != "" and domain not in self.allowed_domains

        if key == "command_matches":
            cmd = params.get("command", "")
            return matches(value, cmd)

        if key == "path_matches":
            p = params.get("path", "")
            return matches(value, p)

        if key == "file_count_exceeds":
            count = params.get("file_count", 0)
            return count > int(value)

        if key == "request_count_in_window":
            return self._check_rate_limit(value)

        if key == "response_content_matches":
            content = params.get("response_body", "") or params.get("content", "")
            return self._eval_content_match(value, content)

        return False

    def _eval_content_match(self, spec, content: str) -> bool:
        """Handle response_content_matches with any/all."""
        if isinstance(spec, dict):
            if "any" in spec:
                return any(matches(p, content) for p in spec["any"])
            if "all" in spec:
                return all(matches(p, content) for p in spec["all"])
        if isinstance(spec, str):
            return matches(spec, content)
        if isinstance(spec, list):
            return any(matches(p, content) for p in spec)
        return False

    def _check_rate_limit(self, value: dict) -> bool:
        max_count = value.get("count", 10)
        window = value.get("window_seconds", 60)
        now = time.monotonic()
        with self._lock:
            self._request_log.append(now)
            cutoff = now - window
            self._request_log = [t for t in self._request_log if t > cutoff]
            return len(self._request_log) > max_count

    @staticmethod
    def _extract_content(params: dict) -> str:
        parts = []
        for k in ("body", "content", "message", "data", "headers"):
            v = params.get(k)
            if v:
                parts.append(str(v))
        url = params.get("url", "")
        if url:
            parts.append(url)
        return "\n".join(parts)

    @staticmethod
    def _extract_domain(url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            return parsed.hostname or ""
        except Exception:
            return ""
