from __future__ import annotations

import hashlib
import json
import time
import threading
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml

from .models import Rule
from .patterns import matches


AFP_REMOTE_RULES_URL = "https://raw.githubusercontent.com/joevise/agent-firewall-protocol/main/rules/core/default-rules.yaml"
AFP_COMMUNITY_RULES_URL = "https://raw.githubusercontent.com/joevise/agent-firewall-protocol/main/rules/community/"


class RemoteRuleLoader:
    """Load rules from a remote URL with local caching."""

    def __init__(self, url: str, cache_dir: str | None = None, cache_ttl: int = 3600):
        self.url = url
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".afp" / "cache"
        self.cache_ttl = cache_ttl

    def _cache_path(self) -> Path:
        h = hashlib.sha256(self.url.encode()).hexdigest()[:16]
        return self.cache_dir / f"{h}.yaml"

    def _meta_path(self) -> Path:
        return self._cache_path().with_suffix(".meta")

    def _is_cache_valid(self) -> bool:
        meta = self._meta_path()
        if not meta.exists() or not self._cache_path().exists():
            return False
        try:
            data = json.loads(meta.read_text())
            return (time.time() - data.get("fetched_at", 0)) < self.cache_ttl
        except Exception:
            return False

    def _fetch_remote(self) -> str | None:
        try:
            req = Request(self.url, headers={"User-Agent": "AFP-SDK/0.1"})
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except (URLError, OSError, Exception):
            return None

    def _save_cache(self, content: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path().write_text(content)
        self._meta_path().write_text(json.dumps({"fetched_at": time.time(), "url": self.url}))

    def _load_cached(self) -> str | None:
        p = self._cache_path()
        return p.read_text() if p.exists() else None

    def load(self) -> list[Rule]:
        """Fetch rules from remote, with local cache fallback."""
        if self._is_cache_valid():
            content = self._load_cached()
            if content:
                return _parse_rules_yaml(content)

        content = self._fetch_remote()
        if content:
            self._save_cache(content)
            return _parse_rules_yaml(content)

        # Stale cache fallback
        content = self._load_cached()
        if content:
            return _parse_rules_yaml(content)
        return []

    def update(self) -> bool:
        """Force update from remote, return True if rules changed."""
        old = self._load_cached()
        content = self._fetch_remote()
        if content is None:
            return False
        self._save_cache(content)
        return content != old


def _parse_rules_yaml(content: str) -> list[Rule]:
    """Parse YAML string into Rule list."""
    rules: list[Rule] = []
    for doc in yaml.safe_load_all(content):
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
