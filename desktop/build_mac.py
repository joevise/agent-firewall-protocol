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

    args = [
        os.path.join(here, 'app.py'),
        '--name=AFP',
        '--onefile',
        '--windowed',
        f'--add-data={os.path.join(root, "sdk", "python", "src", "afp")}:afp',
        f'--add-data={os.path.join(root, "daemon")}:daemon',
        '--hidden-import=pystray',
        '--hidden-import=PIL',
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
