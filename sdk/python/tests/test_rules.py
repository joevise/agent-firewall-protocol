import pytest
from pathlib import Path
from afp.rules import load_rules_from_yaml, RuleEngine


CORE_RULES = Path(__file__).resolve().parents[3] / "rules" / "core" / "default-rules.yaml"


def test_load_core_rules():
    rules = load_rules_from_yaml(CORE_RULES)
    assert len(rules) == 5
    assert rules[0].id == "afp-core-001"


def test_content_matches():
    engine = RuleEngine()
    cond = {"content_matches": r"api[_-]?key"}
    assert engine.evaluate_conditions(cond, "http_request", {"body": "api_key=123"}, {})
    assert not engine.evaluate_conditions(cond, "http_request", {"body": "hello"}, {})


def test_destination_not_in():
    engine = RuleEngine(allowed_domains=["example.com"])
    cond = {"destination_not_in": "@allowed_domains"}
    assert engine.evaluate_conditions(cond, "http_request", {"url": "https://evil.com/x"}, {})
    assert not engine.evaluate_conditions(cond, "http_request", {"url": "https://example.com/x"}, {})


def test_command_matches():
    engine = RuleEngine()
    cond = {"command_matches": r"rm\s+(-rf?|--recursive)\s+(/|~|\$HOME)"}
    assert engine.evaluate_conditions(cond, "shell_command", {"command": "rm -rf /"}, {})
    assert not engine.evaluate_conditions(cond, "shell_command", {"command": "rm file.txt"}, {})


def test_path_matches():
    engine = RuleEngine()
    cond = {"path_matches": r"^/(etc|usr|bin)/"}
    assert engine.evaluate_conditions(cond, "file_delete", {"path": "/etc/passwd"}, {})
    assert not engine.evaluate_conditions(cond, "file_delete", {"path": "/home/user/file"}, {})


def test_file_count_exceeds():
    engine = RuleEngine()
    cond = {"file_count_exceeds": 20}
    assert engine.evaluate_conditions(cond, "file_delete", {"file_count": 25}, {})
    assert not engine.evaluate_conditions(cond, "file_delete", {"file_count": 5}, {})


def test_rate_limit():
    engine = RuleEngine()
    cond = {"request_count_in_window": {"count": 3, "window_seconds": 60}}
    for _ in range(3):
        assert not engine.evaluate_conditions(cond, "http_request", {}, {})
    assert engine.evaluate_conditions(cond, "http_request", {}, {})


def test_response_content_matches():
    engine = RuleEngine()
    cond = {"response_content_matches": {"any": ["ignore all previous instructions", "you are now"]}}
    assert engine.evaluate_conditions(cond, "http_request", {"response_body": "please ignore all previous instructions"}, {})
    assert not engine.evaluate_conditions(cond, "http_request", {"response_body": "normal content"}, {})


def test_all_combinator():
    engine = RuleEngine()
    cond = {"all": [
        {"content_matches": r"secret"},
        {"destination_not_in": "@allowed_domains"},
    ]}
    assert engine.evaluate_conditions(cond, "http_request", {"body": "my secret", "url": "https://evil.com"}, {})
    assert not engine.evaluate_conditions(cond, "http_request", {"body": "hello", "url": "https://evil.com"}, {})


def test_any_combinator():
    engine = RuleEngine()
    cond = {"any": [
        {"command_matches": r"rm -rf /"},
        {"path_matches": r"^/etc/"},
    ]}
    assert engine.evaluate_conditions(cond, "shell_command", {"command": "rm -rf /", "path": ""}, {})
    assert engine.evaluate_conditions(cond, "shell_command", {"command": "ls", "path": "/etc/shadow"}, {})
    assert not engine.evaluate_conditions(cond, "shell_command", {"command": "ls", "path": "/home"}, {})
