"""AFP Desktop — Detect running AI agents on the system."""

import os
import platform
import subprocess
from pathlib import Path


KNOWN_AGENTS = {
    'openclaw': {
        'process_names': ['openclaw', 'node'],
        'indicators': ['.openclaw'],
        'display_name': 'OpenClaw',
    },
    'lm_studio': {
        'process_names': ['LM Studio', 'lms'],
        'indicators': ['.cache/lm-studio'],
        'display_name': 'LM Studio',
    },
    'cursor': {
        'process_names': ['Cursor', 'cursor'],
        'indicators': ['.cursor'],
        'display_name': 'Cursor',
    },
    'cherry_studio': {
        'process_names': ['Cherry Studio', 'cherry-studio'],
        'indicators': [],
        'display_name': 'Cherry Studio',
    },
    'claude_desktop': {
        'process_names': ['Claude'],
        'indicators': ['.config/Claude', 'Library/Application Support/Claude'],
        'display_name': 'Claude Desktop',
    },
    'chatbox': {
        'process_names': ['Chatbox', 'chatbox'],
        'indicators': [],
        'display_name': 'Chatbox',
    },
}


class AgentScanner:
    """Scan the local system for known AI agents."""

    def __init__(self):
        self._process_list: list[str] | None = None

    def _get_process_list(self) -> list[str]:
        """Get list of running process names."""
        if self._process_list is not None:
            return self._process_list
        try:
            if platform.system() == 'Windows':
                out = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'],
                                              text=True, timeout=10)
                self._process_list = [line.split(',')[0].strip('"') for line in out.splitlines() if line.strip()]
            else:
                out = subprocess.check_output(['ps', 'axo', 'comm'], text=True, timeout=10)
                self._process_list = [line.strip() for line in out.splitlines()[1:] if line.strip()]
        except Exception:
            self._process_list = []
        return self._process_list

    def _check_running(self, process_names: list[str]) -> tuple[bool, int | None]:
        """Check if any of the given process names are running."""
        procs = self._get_process_list()
        for pname in process_names:
            for proc in procs:
                if pname.lower() in proc.lower():
                    # Try to get PID
                    try:
                        if platform.system() != 'Windows':
                            result = subprocess.check_output(
                                ['pgrep', '-f', pname], text=True, timeout=5
                            ).strip().split('\n')
                            return True, int(result[0])
                    except Exception:
                        pass
                    return True, None
        return False, None

    def _check_installed(self, indicators: list[str]) -> bool:
        """Check if config directories exist in home."""
        home = Path.home()
        for indicator in indicators:
            if (home / indicator).exists():
                return True
        return False

    def scan(self) -> list[dict]:
        """Scan for AI agents. Returns list of detected agents."""
        self._process_list = None  # Reset cache
        detected = []
        for agent_id, info in KNOWN_AGENTS.items():
            running, pid = self._check_running(info['process_names'])
            installed = self._check_installed(info['indicators'])
            if running or installed:
                detected.append({
                    'id': agent_id,
                    'name': info['display_name'],
                    'status': 'running' if running else 'installed',
                    'pid': pid,
                })
        return detected
