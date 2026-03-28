"""Tests for remote rule loading and URL-based firewall init."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from afp.rules import RemoteRuleLoader, _parse_rules_yaml
from afp.firewall import AgentFirewall

SAMPLE_YAML = """---
rule:
  id: "TEST-001"
  name: "Test Rule"
  description: "A test rule"
  category: "test"
  severity: "high"
  trigger:
    action_type: ["http_request"]
  conditions:
    content_matches: "sk-[a-zA-Z0-9]{20,}"
  action: "block"
  message: "API key detected"
"""


class TestParseRulesYaml:
    def test_parse_valid(self):
        rules = _parse_rules_yaml(SAMPLE_YAML)
        assert len(rules) == 1
        assert rules[0].id == "TEST-001"
        assert rules[0].action == "block"

    def test_parse_empty(self):
        assert _parse_rules_yaml("") == []
        assert _parse_rules_yaml("---\nfoo: bar") == []


class TestRemoteRuleLoader:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _loader(self, url: str = "https://example.com/rules.yaml") -> RemoteRuleLoader:
        return RemoteRuleLoader(url, cache_dir=self.tmpdir, cache_ttl=60)

    @patch("afp.rules.urlopen")
    def test_cache_miss_fetches_remote(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        loader = self._loader()
        rules = loader.load()
        assert len(rules) == 1
        assert rules[0].id == "TEST-001"
        mock_urlopen.assert_called_once()

    @patch("afp.rules.urlopen")
    def test_cache_hit_no_fetch(self, mock_urlopen):
        loader = self._loader()
        # Pre-populate cache
        loader._save_cache(SAMPLE_YAML)

        rules = loader.load()
        assert len(rules) == 1
        mock_urlopen.assert_not_called()

    @patch("afp.rules.urlopen")
    def test_cache_expired_fetches(self, mock_urlopen):
        loader = self._loader()
        loader.cache_ttl = 0  # Expire immediately
        loader._save_cache(SAMPLE_YAML)
        # Ensure meta shows old timestamp
        meta = json.loads(loader._meta_path().read_text())
        meta["fetched_at"] = time.time() - 100
        loader._meta_path().write_text(json.dumps(meta))

        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        rules = loader.load()
        assert len(rules) == 1
        mock_urlopen.assert_called_once()

    @patch("afp.rules.urlopen", side_effect=Exception("network error"))
    def test_fetch_failure_stale_cache(self, mock_urlopen):
        loader = self._loader()
        loader.cache_ttl = 0
        loader._save_cache(SAMPLE_YAML)
        meta = json.loads(loader._meta_path().read_text())
        meta["fetched_at"] = time.time() - 100
        loader._meta_path().write_text(json.dumps(meta))

        rules = loader.load()
        assert len(rules) == 1  # Stale cache used
        assert rules[0].id == "TEST-001"

    @patch("afp.rules.urlopen", side_effect=Exception("network error"))
    def test_fetch_failure_no_cache(self, mock_urlopen):
        loader = self._loader()
        rules = loader.load()
        assert rules == []

    @patch("afp.rules.urlopen")
    def test_update_returns_true_on_change(self, mock_urlopen):
        loader = self._loader()
        loader._save_cache("old content")

        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        assert loader.update() is True

    @patch("afp.rules.urlopen")
    def test_update_returns_false_no_change(self, mock_urlopen):
        loader = self._loader()
        loader._save_cache(SAMPLE_YAML)

        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        assert loader.update() is False


class TestFirewallURLInit:
    @patch("afp.rules.urlopen")
    def test_url_based_init(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        fw = AgentFirewall(rules="https://example.com/rules.yaml")
        result = fw.check("http_request", {"body": "my key sk-abcdefghijklmnopqrstuvwxyz"})
        assert not result.allowed

    @patch("afp.rules.urlopen")
    def test_community_init(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = SAMPLE_YAML.encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        fw = AgentFirewall(rules="community")
        assert len(fw._rules) == 1

    def test_local_file_init(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(SAMPLE_YAML)
            f.flush()
            fw = AgentFirewall(rules=f.name)
            assert len(fw._rules) == 1
