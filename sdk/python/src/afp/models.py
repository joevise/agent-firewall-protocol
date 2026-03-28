from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Rule:
    """A single firewall rule."""
    id: str
    name: str
    description: str
    category: str
    severity: str
    trigger_actions: list[str]
    conditions: dict
    action: str
    message: str = ""


@dataclass
class CheckResult:
    """Result of checking an action against the firewall."""
    allowed: bool
    action: str  # "allow", "block", "alert", "require_confirmation"
    rule_id: str | None = None
    rule_name: str | None = None
    reason: str | None = None
    severity: str | None = None
