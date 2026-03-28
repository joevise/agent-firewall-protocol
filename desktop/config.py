"""AFP Desktop — Configuration management."""

from dataclasses import dataclass, field
import json
from pathlib import Path

AFP_CONFIG_DIR = Path.home() / '.afp'
AFP_CONFIG_FILE = AFP_CONFIG_DIR / 'config.json'

DEFAULT_ALLOWED_DOMAINS = [
    "api.openai.com",
    "api.anthropic.com",
    "api.minimax.chat",
    "dashscope.aliyuncs.com",
    "api.cohere.com",
    "api.mistral.ai",
    "generativelanguage.googleapis.com",
    "api.groq.com",
    "api.together.xyz",
    "huggingface.co",
    "github.com",
    "raw.githubusercontent.com",
]


@dataclass
class AFPConfig:
    proxy_port: int = 9999
    dashboard_port: int = 9998
    rules_source: str = "community"
    allowed_domains: list = field(default_factory=lambda: list(DEFAULT_ALLOWED_DOMAINS))
    auto_start_proxy: bool = True
    auto_set_system_proxy: bool = True
    scan_interval_seconds: int = 300

    def save(self) -> None:
        AFP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        AFP_CONFIG_FILE.write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls) -> 'AFPConfig':
        if AFP_CONFIG_FILE.exists():
            try:
                data = json.loads(AFP_CONFIG_FILE.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()
