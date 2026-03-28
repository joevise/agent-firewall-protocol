# Contributing to Agent Firewall Protocol

Thank you for your interest in making AI agents safer! Here's how you can contribute.

## Contributing Rules

### Rule Format

All rules must follow the schema defined in `rules/schema.yaml`. Here's a minimal example:

```yaml
version: "1.0"
rule:
  id: "afp-community-001"
  name: "your-rule-name"
  description: "What this rule does"
  category: "data-flow"  # or: tool-access, rate-limit, content-filter, anomaly
  severity: "high"       # or: low, medium, critical
  trigger:
    action_type: ["http_request"]
  conditions:
    all:
      - your_condition_here
  action: block          # or: allow, alert, require_confirmation
  metadata:
    author: "your-github-username"
    created: "YYYY-MM-DD"
```

### Submission Process

1. **Fork** this repository
2. **Create** a new YAML file in `rules/community/` with your rule(s)
3. **Test** your rule using the AFP SDK test framework (see below)
4. **Submit** a Pull Request with:
   - A clear description of the threat this rule addresses
   - At least one example of the attack it prevents
   - Any references (CVEs, blog posts, research papers)

### Review Process

- At least 2 maintainers must approve
- Rules are tested against the example attack scenarios
- Merged rules are included in the next community rules update

## Contributing Code

### Setup Development Environment

```bash
git clone https://github.com/joevise/agent-firewall-protocol.git
cd agent-firewall-protocol
cd sdk/python
pip install -e ".[dev]"
```

### Code Standards

- Python: Follow PEP 8, use type hints
- TypeScript: Follow ESLint config
- All code must have tests
- Documentation for public APIs

## Reporting Vulnerabilities

If you find a way to bypass AFP rules, **please report it responsibly**:

1. **Do NOT** open a public GitHub issue
2. Email: (TBD — set up security email)
3. We will acknowledge within 48 hours
4. Fix will be prioritized based on severity

## Code of Conduct

Be respectful. We're all here to make AI safer for everyone.
