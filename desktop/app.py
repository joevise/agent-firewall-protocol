"""AFP Desktop — Agent Firewall Protocol desktop application.

Cross-platform system-tray app that runs the AFP proxy, scans for local
AI agents, and provides a dashboard for monitoring and rule management.
"""

import logging
import os
import signal
import sys
import threading
import time

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

        self._proxy_thread: threading.Thread | None = None
        self._dashboard_thread: threading.Thread | None = None
        self._scanner_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Rules ──

    def load_rules(self):
        """Load AFP firewall rules from SDK."""
        try:
            from afp.firewall import AgentFirewall
            self.firewall = AgentFirewall()
            self.rule_count = len(getattr(self.firewall, 'rules', []))
            logger.info('Loaded %d AFP rules', self.rule_count)
        except Exception as e:
            logger.warning('Could not load AFP SDK rules: %s', e)
            self.firewall = None
            self.rule_count = 0

    # ── Proxy server ──

    def _run_proxy(self):
        try:
            from daemon.proxy import start_proxy
            logger.info('Starting AFP proxy on port %d', self.config.proxy_port)
            self.proxy_running = True
            start_proxy(port=self.config.proxy_port)
        except ImportError:
            logger.warning('daemon.proxy not available — running stub proxy')
            self.proxy_running = True
            self._stop_event.wait()  # Block until stop
        except Exception as e:
            logger.error('Proxy failed: %s', e)
        finally:
            self.proxy_running = False

    def _start_proxy(self):
        self._proxy_thread = threading.Thread(target=self._run_proxy, daemon=True, name='afp-proxy')
        self._proxy_thread.start()

    # ── Dashboard server ──

    def _run_dashboard(self):
        try:
            from daemon.dashboard import start_dashboard
            logger.info('Starting AFP dashboard on port %d', self.config.dashboard_port)
            self.dashboard_running = True
            start_dashboard(port=self.config.dashboard_port)
        except ImportError:
            logger.warning('daemon.dashboard not available — dashboard disabled')
            self.dashboard_running = True
            self._stop_event.wait()
        except Exception as e:
            logger.error('Dashboard failed: %s', e)
        finally:
            self.dashboard_running = False

    def _start_dashboard(self):
        self._dashboard_thread = threading.Thread(target=self._run_dashboard, daemon=True, name='afp-dashboard')
        self._dashboard_thread.start()

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

        # 3. Start proxy
        if self.config.auto_start_proxy:
            self._start_proxy()

        # 4. Start dashboard
        self._start_dashboard()

        # 5. Configure system proxy
        if self.config.auto_set_system_proxy:
            try:
                self.proxy_manager.enable()
            except Exception as e:
                logger.warning('Could not set system proxy: %s', e)

        # 6. Start periodic scanner
        self._start_scanner()

        # 7. Run tray (blocking — runs in main thread)
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
