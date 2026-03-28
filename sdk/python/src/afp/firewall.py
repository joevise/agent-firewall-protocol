from __future__ import annotations

from pathlib import Path

from .models import Rule, CheckResult
from .rules import RuleEngine, load_rules_from_yaml, load_rules_from_dir


_CORE_RULES_DIR = Path(__file__).resolve().parents[4] / "rules" / "core"


class AgentFirewall:
    """Main entry point for the Agent Firewall Protocol."""

    def __init__(
        self,
        rules: str = "core",
        rules_dir: str | None = None,
        custom_rules: list[Rule] | None = None,
        allowed_domains: list[str] | None = None,
    ):
        self._rules: list[Rule] = []
        self._engine = RuleEngine(allowed_domains=allowed_domains)

        if rules == "core" and rules_dir is None:
            if _CORE_RULES_DIR.exists():
                self._rules.extend(load_rules_from_dir(_CORE_RULES_DIR))
        elif rules_dir:
            self._rules.extend(load_rules_from_dir(rules_dir))

        if custom_rules:
            self._rules.extend(custom_rules)

    def check(self, action: str, params: dict, context: dict | None = None) -> CheckResult:
        """Check an action against all loaded rules."""
        ctx = context or {}
        for rule in self._rules:
            if action not in rule.trigger_actions:
                continue
            if self._engine.evaluate_conditions(rule.conditions, action, params, ctx):
                return CheckResult(
                    allowed=rule.action in ("allow", "alert"),
                    action=rule.action,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    reason=rule.message,
                    severity=rule.severity,
                )
        return CheckResult(allowed=True, action="allow")

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def load_rules(self, path: str) -> None:
        p = Path(path)
        if p.is_dir():
            self._rules.extend(load_rules_from_dir(p))
        else:
            self._rules.extend(load_rules_from_yaml(p))
