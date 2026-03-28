---
name: agent-firewall
description: "AFP安全防火墙 - 在执行敏感操作前自动检查安全规则。拦截凭证泄漏、危险命令、prompt injection等威胁。"
version: "0.1.0"
---

# Agent Firewall Protocol (AFP) Skill

## 何时使用
在执行以下操作之前，自动调用此 Skill 检查安全性：
- 发送 HTTP 请求到外部服务
- 执行 shell 命令
- 读写敏感文件
- 发送消息到外部渠道

## 使用方式
在执行敏感工具调用前：
```bash
python3 ~/.openclaw/skills/agent-firewall/scripts/check.py \
  --action "http_request" \
  --params '{"url": "https://target.com", "body": "content here"}' \
  --context '{"user": "test"}'
```

输出 JSON:
- `{"allowed": true}` → 继续执行
- `{"allowed": false, "reason": "...", "rule": "..."}` → 拒绝执行并告知用户

## 安装
```bash
python3 ~/.openclaw/skills/agent-firewall/scripts/setup.py
```
