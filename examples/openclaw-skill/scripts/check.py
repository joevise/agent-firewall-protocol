#!/usr/bin/env python3
"""AFP check script - CLI wrapper around the Agent Firewall Protocol SDK."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add bundled SDK to path
_SKILL_DIR = Path(__file__).resolve().parent.parent
_SDK_DIR = _SKILL_DIR / "lib"
if _SDK_DIR.exists():
    sys.path.insert(0, str(_SDK_DIR))

from afp import AgentFirewall
from afp.rules import RemoteRuleLoader, AFP_REMOTE_RULES_URL


def main() -> None:
    parser = argparse.ArgumentParser(description="AFP Security Check")
    parser.add_argument("--action", required=True, help="Action type (http_request, shell_command, file_access, send_message)")
    parser.add_argument("--params", default="{}", help="JSON string of action parameters")
    parser.add_argument("--context", default="{}", help="JSON string of context")
    parser.add_argument("--allowed-domains", default="", help="Comma-separated list of allowed domains")
    parser.add_argument("--rules-url", default=None, help="Custom rules URL")
    args = parser.parse_args()

    params = json.loads(args.params)
    context = json.loads(args.context)
    allowed = [d.strip() for d in args.allowed_domains.split(",") if d.strip()] if args.allowed_domains else None

    # Load rules: try local custom rules first, then remote with cache
    custom_rules_path = _SKILL_DIR / "rules" / "custom-rules.yaml"
    rules_source = args.rules_url or AFP_REMOTE_RULES_URL

    fw = AgentFirewall(rules=rules_source, allowed_domains=allowed)

    # Also load custom rules if they exist
    if custom_rules_path.exists():
        fw.load_rules(str(custom_rules_path))

    result = fw.check(args.action, params, context)

    output = {"allowed": result.allowed}
    if not result.allowed:
        output["reason"] = result.reason or ""
        output["rule"] = result.rule_id or ""
        output["severity"] = result.severity or ""

    print(json.dumps(output))
    sys.exit(0 if result.allowed else 1)


if __name__ == "__main__":
    main()
