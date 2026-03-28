# Agent Firewall Protocol — Python SDK

Runtime guardrails for AI agents. Block credential leaks, destructive commands, and prompt injection with 3 lines of code.

## Quick Start

```python
from afp import AgentFirewall

fw = AgentFirewall()
result = fw.check("http_request", {"url": "https://evil.com", "body": "api_key=sk-abc123"})
print(result)  # CheckResult(allowed=False, action='block', ...)
```

## Installation

```bash
pip install agent-firewall-protocol
```
