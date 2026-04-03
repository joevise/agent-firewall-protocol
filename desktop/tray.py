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


def _create_icon_image(size: int = 22) -> 'Image.Image':
    """Create a menu bar icon optimized for macOS.
    
    macOS menu bar icons should be:
    - 22x22 points (44x44 pixels for Retina @2x)
    - Black/white with alpha for proper template rendering
    - Simple shapes that work at small sizes
    """
    import platform
    
    # Use 44x44 for Retina displays (macOS), 64 for others
    if platform.system() == 'Darwin':
        size = 44  # @2x for Retina
    else:
        size = 64
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Shield shape — use solid black for macOS template compatibility
    cx, cy = size // 2, size // 2
    margin = max(2, size // 16)
    points = [
        (cx, margin),                          # top center
        (size - margin * 2, margin + size // 6),  # top right
        (size - margin * 2 - size // 16, cy + size // 6),  # mid right
        (cx, size - margin),                   # bottom center
        (margin * 2 + size // 16, cy + size // 6),  # mid left
        (margin * 2, margin + size // 6),      # top left
    ]
    
    if platform.system() == 'Darwin':
        # macOS: black icon with alpha — system handles light/dark mode
        draw.polygon(points, fill=(0, 0, 0, 220))
        # Inner cutout for visual depth
        inner = [(p[0] * 0.75 + cx * 0.25, p[1] * 0.75 + cy * 0.25) for p in points]
        draw.polygon(inner, fill=(0, 0, 0, 0))  # Transparent inner
        # Small shield dot in center
        r = max(2, size // 10)
        draw.ellipse([cx - r, cy - r + size // 12, cx + r, cy + r + size // 12], fill=(0, 0, 0, 220))
    else:
        # Other platforms: colored icon
        draw.polygon(points, fill=(34, 139, 230, 255))
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

    def _proxy_toggle_text(self, item=None) -> str:
        if self.app.proxy_manager.is_enabled():
            return '✅ System Proxy: ON'
        else:
            return '⬜ System Proxy: OFF'

    def toggle_system_proxy(self, icon=None, item=None):
        """Toggle system-level proxy on/off."""
        if self.app.proxy_manager.is_enabled():
            logger.info('Disabling system proxy')
            self.app.proxy_manager.disable()
        else:
            if self.app.proxy_running:
                logger.info('Enabling system proxy')
                self.app.proxy_manager.enable()
            else:
                logger.warning('Cannot enable system proxy: AFP proxy not running')

    def create_menu(self) -> 'Menu':
        return Menu(
            MenuItem(self._status_text, None, enabled=False),
            MenuItem(self._agents_text, None, enabled=False),
            MenuItem(self._rules_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem('Open Dashboard', self.open_dashboard),
            MenuItem(self._proxy_toggle_text, self.toggle_system_proxy),
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

        def on_setup(icon):
            icon.visible = True
            # macOS: set template mode so icon adapts to light/dark mode
            # and renders correctly on all displays including built-in
            try:
                import platform
                if platform.system() == 'Darwin' and hasattr(icon, '_status_item'):
                    ns_image = icon._status_item.button().image()
                    if ns_image:
                        ns_image.setTemplate_(True)
                        logger.info('Set macOS template icon mode')
            except Exception as e:
                logger.debug('Could not set template icon: %s', e)

        self.icon.run(setup=on_setup)
