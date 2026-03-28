"""Build AFP Desktop for macOS using PyInstaller."""

import os
import sys

def build():
    try:
        import PyInstaller.__main__
    except ImportError:
        print('ERROR: PyInstaller not installed. Run: pip install pyinstaller>=6.0')
        sys.exit(1)

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)

    daemon_dir = os.path.join(root, 'daemon')
    sdk_dir = os.path.join(root, 'sdk', 'python', 'src')

    args = [
        os.path.join(here, 'app.py'),
        '--name=AFP',
        '--onefile',
        '--windowed',
        # Add project root so 'daemon' package is importable as 'daemon.proxy' etc.
        # Add daemon dir so bare 'from logger import ...' inside daemon/ works
        f'--paths={root}',
        f'--paths={daemon_dir}',
        f'--paths={sdk_dir}',
        f'--paths={here}',
        # Collect daemon package as additional source files for analysis
        f'--collect-submodules=daemon',
        # Data files (dashboard HTML)
        f'--add-data={os.path.join(daemon_dir, "static")}:daemon/static',
        # Hidden imports for modules PyInstaller can't trace from app.py
        '--hidden-import=proxy',
        '--hidden-import=dashboard',
        '--hidden-import=logger',
        '--hidden-import=config',
        '--hidden-import=agent_scanner',
        '--hidden-import=proxy_manager',
        '--hidden-import=tray',
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        '--hidden-import=yaml',
        '--hidden-import=pystray._darwin',
        '--collect-all=pystray',
        '--collect-all=yaml',
        '--osx-bundle-identifier=com.agentfirewall.afp',
    ]

    icon = os.path.join(here, 'assets', 'icon.png')
    if os.path.exists(icon):
        args.append(f'--icon={icon}')

    rules_dir = os.path.join(root, 'rules')
    if os.path.isdir(rules_dir):
        args.append(f'--add-data={rules_dir}:rules')

    print(f'Building AFP Desktop for macOS...')
    PyInstaller.__main__.run(args)
    print('Build complete! Check dist/AFP')


if __name__ == '__main__':
    build()
