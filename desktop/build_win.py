"""Build AFP Desktop for Windows using PyInstaller (placeholder)."""

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
        f'--add-data={os.path.join(root, "sdk", "python", "src", "afp")};afp',
        f'--add-data={os.path.join(root, "daemon")};daemon',
        '--hidden-import=pystray',
        '--hidden-import=PIL',
    ]

    icon = os.path.join(here, 'assets', 'icon.ico')
    if os.path.exists(icon):
        args.append(f'--icon={icon}')

    print('Building AFP Desktop for Windows...')
    PyInstaller.__main__.run(args)
    print('Build complete! Check dist/AFP.exe')


if __name__ == '__main__':
    build()
