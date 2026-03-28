# Agent Firewall Protocol (AFP)

<p align="center">
  <strong>🛡️ Decentralized Security Protocol for AI Agents</strong>
</p>

<p align="center">
  <em>Community-driven threat rules • Behavior boundaries • Anomaly detection</em>
</p>

---

## The Problem

AI Agents are replacing traditional software. They read your emails, execute code, manage your files, and interact with the world on your behalf. But they have a fundamental vulnerability:

> **An agent cannot reliably distinguish whose intent is driving its behavior.**

Every input is just text. The agent can't tell whether a command comes from its owner, a malicious webpage, a hallucination, or another compromised agent. This single root cause leads to:

- **Prompt Injection** — External text masquerading as user commands
- **Jailbreaking** — Carefully crafted inputs bypassing safety boundaries
- **Data Exfiltration** — Agents tricked into leaking sensitive information
- **Tool Abuse** — Agents manipulated into calling unauthorized tools
- **Loss of Control** — Agents making autonomous decisions beyond their authority

No single company can solve this. The attack surface is too broad, evolving too fast. **We need a community-driven immune system.**

## The Solution: Agent Firewall Protocol

AFP is an open, decentralized protocol that provides three layers of defense for any AI agent:

```
┌─────────────────────────────────────────────┐
│              AI Agent Runtime                │
├─────────────────────────────────────────────┤
│  Layer 1: Input Isolation                   │
│  Structurally separate instructions from    │
│  external data at the protocol level        │
├─────────────────────────────────────────────┤
│  Layer 2: Behavior Boundary (AFP Core)      │
│  Policy engine enforcing what agents can    │
│  and cannot do — the "firewall rules"       │
├─────────────────────────────────────────────┤
│  Layer 3: Anomaly Detection                 │
│  Real-time behavioral monitoring using      │
│  community-contributed threat signatures    │
├─────────────────────────────────────────────┤
│              AFP Rule Engine                 │
│  Community-maintained, DAO-governed          │
│  threat rules and behavior policies          │
└─────────────────────────────────────────────┘
```

### Layer 1: Input Isolation

Separate user instructions from external data at the structural level — like parameterized queries prevent SQL injection.

### Layer 2: Behavior Boundary (Start Here)

A policy engine that intercepts every agent action and checks it against a rule set:

```yaml
# Example AFP Rule
- rule: block-sensitive-exfiltration
  description: "Prevent sending API keys or credentials to external services"
  trigger: tool_call
  conditions:
    - tool: [http_request, web_fetch, message_send]
    - content_matches: "(api[_-]?key|secret|password|token|credential)"
    - destination_not_in: allowed_domains
  action: block
  severity: critical
```

### Layer 3: Anomaly Detection

Community-contributed behavioral signatures that detect suspicious patterns:

```yaml
# Example Anomaly Signature
- signature: bulk-file-read-then-exfil
  description: "Agent reads multiple files then makes external request"
  pattern:
    - action: file_read (count > 5, window: 60s)
    - followed_by: http_request (destination: external)
  risk: high
```

## How It Works

```
1. Agent wants to call a tool (e.g., send HTTP request)
        ↓
2. AFP SDK intercepts the call
        ↓
3. Check against local rule cache
        ↓
4. ✅ Rule allows → Execute normally
   ❌ Rule blocks → Reject + Alert user
   ⚠️ No rule matches → Log for review
        ↓
5. Behavior logged for anomaly detection
```

## DAO Governance (Future)

The rule database is AFP's core asset. In later phases, governance transitions to a DAO:

- **Contributors** submit new rules and threat signatures → earn rewards
- **Reviewers** validate and audit submissions → earn rewards
- **Users** (agent platforms, enterprises) consume rules → fund the ecosystem
- **Token holders** vote on rule priorities, protocol upgrades, and treasury allocation

> **Note:** Phase 1 is pure open source. No tokens, no blockchain. Just good security engineering and community collaboration.

## Roadmap

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Phase 1** | Now | Open source AFP SDK + rule engine + initial rule set |
| **Phase 2** | +3 months | Multi-framework integration (OpenClaw, LangChain, CrewAI) |
| **Phase 3** | +6 months | DAO launch, token-based incentives for contributors |
| **Phase 4** | +12 months | Enterprise features, compliance tools |
| **Phase 5** | +24 months | Industry standard for AI agent security |

## Quick Start

```bash
# Install AFP SDK (coming soon)
pip install agent-firewall-protocol

# In your agent code
from afp import AgentFirewall

firewall = AgentFirewall(rules="community")  # Use community rule set

# Wrap your agent's tool calls
result = firewall.check(
    action="http_request",
    params={"url": "https://api.example.com", "body": data},
    context={"user_id": "...", "session_id": "..."}
)

if result.allowed:
    # Proceed with the action
    execute_tool_call(...)
else:
    # Block and alert
    log.warning(f"AFP blocked: {result.rule_id} — {result.reason}")
```

## Project Structure

```
agent-firewall-protocol/
├── README.md              # This file
├── WHITEPAPER.md           # Full protocol specification
├── LICENSE                 # Apache 2.0
├── rules/                  # Community-maintained rule database
│   ├── core/              # Default rules (always active)
│   ├── community/         # Community-contributed rules
│   └── schema.yaml        # Rule definition schema
├── sdk/                    # AFP SDK implementations
│   ├── python/            # Python SDK
│   └── typescript/        # TypeScript SDK
├── examples/              # Integration examples
│   ├── openclaw/          # OpenClaw integration
│   └── langchain/         # LangChain integration
└── docs/                  # Documentation
    ├── architecture.md    # Technical architecture
    ├── contributing.md    # How to contribute rules
    └── threat-model.md   # AI agent threat taxonomy
```

## Contributing

We're building the immune system for AI agents. Every contribution matters:

- 🛡️ **Submit rules** — Found a new attack pattern? Write a rule for it
- 🔍 **Review rules** — Help validate community submissions
- 💻 **Build SDK** — Help integrate AFP into more agent frameworks
- 📝 **Write docs** — Help others understand AI agent security
- 🐛 **Report issues** — Found a bypass? Let us know

See [CONTRIBUTING.md](docs/contributing.md) for details.

## License

Apache License 2.0 — Free to use, modify, and distribute.

---

<p align="center">
  <strong>AFP — Because AI agents need a firewall too.</strong>
</p>
