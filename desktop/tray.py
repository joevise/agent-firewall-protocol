"""AFP Desktop — System tray icon and menu."""

import logging
import webbrowser

logger = logging.getLogger(__name__)

try:
    from pystray import Icon, MenuItem, Menu
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _create_icon_image(size: int = 64) -> 'Image.Image':
    """Create a simple shield icon programmatically."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Shield shape
    cx, cy = size // 2, size // 2
    points = [
        (cx, 4),          # top center
        (size - 6, 14),   # top right
        (size - 8, cy + 8),  # mid right
        (cx, size - 4),   # bottom center
        (8, cy + 8),      # mid left
        (6, 14),          # top left
    ]
    draw.polygon(points, fill=(34, 139, 230, 255))  # Blue shield
    # Inner highlight
    inner = [(p[0] * 0.8 + cx * 0.2, p[1] * 0.8 + cy * 0.2) for p in points]
    draw.polygon(inner, fill=(59, 170, 255, 180))
    return img


class AFPTray:
    """System tray icon for AFP Desktop."""

    def __init__(self, app):
        self.app = app
        self.icon = None

    def _status_text(self, item=None) -> str:
        return '🛡️ AFP Running' if self.app.proxy_running else '⏸️ AFP Stopped'

    def _agents_text(self, item=None) -> str:
        return f'Agents: {len(self.app.agents_detected)}'

    def _rules_text(self, item=None) -> str:
        return f'Rules: {self.app.rule_count}'

    def _build_agent_submenu(self):
        items = []
        for agent in self.app.agents_detected:
            status = '🟢' if agent['status'] == 'running' else '⚪'
            items.append(MenuItem(f"{status} {agent['name']}", None, enabled=False))
        if not items:
            items.append(MenuItem('No agents detected', None, enabled=False))
        return Menu(*items)

    def create_menu(self) -> 'Menu':
        return Menu(
            MenuItem(self._status_text, None, enabled=False),
            MenuItem(self._agents_text, None, enabled=False),
            MenuItem(self._rules_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem('Open Dashboard', self.open_dashboard),
            MenuItem('Update Rules', self.update_rules),
            Menu.SEPARATOR,
            MenuItem('Detected Agents', self._build_agent_submenu()),
            Menu.SEPARATOR,
            MenuItem('Quit', self.quit),
        )

    def open_dashboard(self, icon=None, item=None):
        webbrowser.open(f'http://localhost:{self.app.config.dashboard_port}')

    def update_rules(self, icon=None, item=None):
        logger.info('Updating AFP rules...')
        try:
            self.app.load_rules()
            logger.info('Rules updated successfully')
        except Exception as e:
            logger.error('Failed to update rules: %s', e)

    def quit(self, icon=None, item=None):
        logger.info('Quit requested from tray')
        self.app.stop()
        if self.icon:
            self.icon.stop()

    def run(self):
        if not HAS_TRAY:
            logger.warning('pystray not available — tray icon disabled')
            return
        image = _create_icon_image()
        self.icon = Icon('AFP', image, 'Agent Firewall Protocol', menu=self.create_menu())
        logger.info('Starting system tray icon')
        self.icon.run()
