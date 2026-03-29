"""AFP Desktop — Agent Firewall Protocol desktop application.

Cross-platform system-tray app that runs the AFP proxy, scans for local
AI agents, and provides a dashboard for monitoring and rule management.
"""

import logging
import os
import signal
import socket
import sys
import threading
import time
import webbrowser

# Add project root to path so we can import daemon and SDK
# Handle both development mode and PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BUNDLE_DIR = sys._MEIPASS
    sys.path.insert(0, BUNDLE_DIR)
    sys.path.insert(0, os.path.join(BUNDLE_DIR, 'daemon'))
else:
    # Running from source
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'daemon'))
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'sdk', 'python', 'src'))
    sys.path.insert(0, os.path.dirname(__file__))

from config import AFPConfig
from agent_scanner import AgentScanner
from proxy_manager import ProxyManager
from tray import AFPTray

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('afp.desktop')


class AFPDesktopApp:
    """Main AFP Desktop application."""

    def __init__(self):
        self.config = AFPConfig.load()
        self.proxy_running = False
        self.dashboard_running = False
        self.agents_detected: list[dict] = []
        self.rule_count = 0
        self.firewall = None

        self.scanner = AgentScanner()
        self.proxy_manager = ProxyManager(proxy_port=self.config.proxy_port)
        self.tray = AFPTray(self)

        self._proxy_server = None
        self._dashboard_server = None
        self._scanner_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Rules ──

    def load_rules(self):
        """Load AFP firewall rules from SDK."""
        try:
            from afp.firewall import AgentFirewall
            self.firewall = AgentFirewall()
            self.rule_count = len(getattr(self.firewall, '_rules', []))
            logger.info('Loaded %d AFP rules', self.rule_count)
        except Exception as e:
            logger.warning('Could not load AFP SDK rules: %s', e)
            self.firewall = None
            self.rule_count = 0

    # ── Proxy server ──

    def _start_proxy(self):
        """Start the proxy server and block until it's actually listening."""
        try:
            import daemon.proxy as proxy_mod
            from daemon.logger import AFPLogger as DaemonLogger
            proxy_mod.firewall = self.firewall
            proxy_mod.logger = DaemonLogger(max_events=1000)
            self._daemon_logger = proxy_mod.logger
            logger.info('Starting AFP proxy on port %d', self.config.proxy_port)
            # Kill any stale process on this port
            self._kill_port(self.config.proxy_port)
            self._proxy_server = proxy_mod.start_proxy(port=self.config.proxy_port)
            # Verify it's actually listening
            self._wait_for_port(self.config.proxy_port, timeout=5)
            self.proxy_running = True
            logger.info('AFP proxy is listening on port %d', self.config.proxy_port)
        except Exception as e:
            logger.error('Proxy failed to start: %s', e)
            self.proxy_running = False
            raise

    @staticmethod
    def _wait_for_port(port: int, host: str = '127.0.0.1', timeout: float = 5):
        """Wait until a port is accepting connections."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f'Port {port} not listening after {timeout}s')

    @staticmethod
    def _kill_port(port: int):
        """Kill any process occupying the given port."""
        import subprocess
        try:
            # Find PIDs listening on this port
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True, timeout=5
            )
            pids = result.stdout.strip().split('\n')
            my_pid = str(os.getpid())
            for pid in pids:
                pid = pid.strip()
                if pid and pid != my_pid:
                    logger.info('Killing process %s on port %d', pid, port)
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except (ProcessLookupError, ValueError):
                        pass
            if any(p.strip() and p.strip() != my_pid for p in pids):
                time.sleep(0.5)  # Give processes time to exit
        except FileNotFoundError:
            # lsof not available, try with fuser or just skip
            pass
        except Exception as e:
            logger.warning('Could not kill process on port %d: %s', port, e)

    # ── Dashboard server ──

    def _start_dashboard(self):
        """Start dashboard server and block until it's listening."""
        try:
            import daemon.dashboard as dash_mod
            dash_mod.firewall = self.firewall
            dash_mod.logger = getattr(self, '_daemon_logger', None)
            logger.info('Starting AFP dashboard on port %d', self.config.dashboard_port)
            # Kill any stale process on this port
            self._kill_port(self.config.dashboard_port)
            self._dashboard_server = dash_mod.start_dashboard(port=self.config.dashboard_port)
            self._wait_for_port(self.config.dashboard_port, timeout=5)
            self.dashboard_running = True
            logger.info('AFP dashboard is listening on port %d', self.config.dashboard_port)
        except Exception as e:
            logger.error('Dashboard failed to start: %s', e)
            self.dashboard_running = False

    # ── Agent scanner ──

    def _scan_loop(self):
        while not self._stop_event.is_set():
            try:
                self.agents_detected = self.scanner.scan()
                logger.info('Scan complete: %d agent(s) detected', len(self.agents_detected))
            except Exception as e:
                logger.error('Agent scan failed: %s', e)
            self._stop_event.wait(self.config.scan_interval_seconds)

    def _start_scanner(self):
        self._scanner_thread = threading.Thread(target=self._scan_loop, daemon=True, name='afp-scanner')
        self._scanner_thread.start()

    # ── Lifecycle ──

    def start(self):
        """Start the full AFP Desktop application."""
        logger.info('=== AFP Desktop starting ===')

        # 1. Load rules
        self.load_rules()

        # 2. Initial agent scan
        self.agents_detected = self.scanner.scan()
        logger.info('Detected %d agent(s): %s', len(self.agents_detected),
                     ', '.join(a['name'] for a in self.agents_detected) or 'none')

        # 3. Start proxy FIRST and verify it's listening
        if self.config.auto_start_proxy:
            try:
                self._start_proxy()
            except Exception as e:
                logger.error('Proxy failed to start — will NOT set system proxy: %s', e)
                self.config.auto_set_system_proxy = False

        # 4. Start dashboard
        self._start_dashboard()

        # 5. Configure system proxy ONLY if proxy is confirmed running
        if self.config.auto_set_system_proxy and self.proxy_running:
            try:
                self.proxy_manager.enable()
            except Exception as e:
                logger.warning('Could not set system proxy: %s', e)

        # 6. Auto-open dashboard in browser
        if self.dashboard_running:
            try:
                webbrowser.open(f'http://localhost:{self.config.dashboard_port}')
            except Exception:
                pass

        # 7. Start periodic scanner
        self._start_scanner()

        # 8. Run tray (blocking — runs in main thread)
        logger.info('AFP Desktop ready')
        try:
            self.tray.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Clean shutdown."""
        logger.info('=== AFP Desktop shutting down ===')
        self._stop_event.set()

        # Remove system proxy
        try:
            self.proxy_manager.disable()
        except Exception as e:
            logger.warning('Could not remove system proxy: %s', e)

        # Save config
        try:
            self.config.save()
        except Exception:
            pass

        logger.info('AFP Desktop stopped')


def main():
    app = AFPDesktopApp()
    signal.signal(signal.SIGINT, lambda *_: app.stop())
    signal.signal(signal.SIGTERM, lambda *_: app.stop())
    app.start()


if __name__ == '__main__':
    main()
