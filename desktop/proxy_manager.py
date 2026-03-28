"""AFP Desktop — System proxy configuration."""

import logging
import platform
import subprocess

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages system-level HTTP/HTTPS proxy settings."""

    def __init__(self, proxy_host: str = '127.0.0.1', proxy_port: int = 9999):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.os_type = platform.system()

    # ── macOS helpers ──

    def _mac_services(self) -> list[str]:
        """List active network services on macOS."""
        try:
            out = subprocess.check_output(
                ['networksetup', '-listallnetworkservices'], text=True, timeout=10
            )
            return [l.strip() for l in out.splitlines()[1:] if l.strip() and not l.startswith('*')]
        except Exception as e:
            logger.warning('Failed to list network services: %s', e)
            return []

    def _mac_set_proxy(self, enable: bool) -> bool:
        services = self._mac_services()
        if not services:
            return False
        ok = True
        for svc in services:
            try:
                if enable:
                    subprocess.check_call(
                        ['networksetup', '-setwebproxy', svc, self.proxy_host, str(self.proxy_port)],
                        timeout=10)
                    subprocess.check_call(
                        ['networksetup', '-setsecurewebproxy', svc, self.proxy_host, str(self.proxy_port)],
                        timeout=10)
                else:
                    subprocess.check_call(['networksetup', '-setwebproxystate', svc, 'off'], timeout=10)
                    subprocess.check_call(['networksetup', '-setsecurewebproxystate', svc, 'off'], timeout=10)
            except Exception as e:
                logger.warning('Proxy config failed for %s: %s', svc, e)
                ok = False
        return ok

    # ── Windows helpers ──

    def _win_set_proxy(self, enable: bool) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, 'ProxyServer', 0, winreg.REG_SZ,
                                  f'{self.proxy_host}:{self.proxy_port}')
            else:
                winreg.SetValueEx(key, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.warning('Windows proxy config failed: %s', e)
            return False

    # ── Linux helpers ──

    def _linux_set_proxy(self, enable: bool) -> bool:
        try:
            if enable:
                proxy_url = f'http://{self.proxy_host}:{self.proxy_port}'
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'manual'], timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.http', 'host', self.proxy_host], timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.http', 'port', str(self.proxy_port)], timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.https', 'host', self.proxy_host], timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.https', 'port', str(self.proxy_port)], timeout=5)
            else:
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'none'], timeout=5)
            return True
        except Exception as e:
            logger.warning('Linux proxy config failed: %s', e)
            return False

    # ── Public API ──

    def enable(self) -> bool:
        logger.info('Enabling system proxy → %s:%d', self.proxy_host, self.proxy_port)
        if self.os_type == 'Darwin':
            return self._mac_set_proxy(True)
        elif self.os_type == 'Windows':
            return self._win_set_proxy(True)
        elif self.os_type == 'Linux':
            return self._linux_set_proxy(True)
        return False

    def disable(self) -> bool:
        logger.info('Disabling system proxy')
        if self.os_type == 'Darwin':
            return self._mac_set_proxy(False)
        elif self.os_type == 'Windows':
            return self._win_set_proxy(False)
        elif self.os_type == 'Linux':
            return self._linux_set_proxy(False)
        return False

    def is_enabled(self) -> bool:
        try:
            if self.os_type == 'Darwin':
                services = self._mac_services()
                if not services:
                    return False
                out = subprocess.check_output(
                    ['networksetup', '-getwebproxy', services[0]], text=True, timeout=10)
                return 'Enabled: Yes' in out
            elif self.os_type == 'Windows':
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                    0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(key, 'ProxyEnable')
                winreg.CloseKey(key)
                return bool(val)
            elif self.os_type == 'Linux':
                out = subprocess.check_output(
                    ['gsettings', 'get', 'org.gnome.system.proxy', 'mode'],
                    text=True, timeout=5).strip().strip("'")
                return out == 'manual'
        except Exception:
            pass
        return False
