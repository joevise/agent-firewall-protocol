# AFP Desktop

Cross-platform desktop application for the **Agent Firewall Protocol**.  
Provides a system-tray icon, automatic AI agent detection, proxy management, and a web dashboard.

## Features

- 🛡️ **System Tray** — always-on status indicator with quick actions
- 🔍 **Agent Scanner** — auto-detects OpenClaw, Cursor, LM Studio, Claude Desktop, Cherry Studio, Chatbox
- 🌐 **Proxy Manager** — configures system HTTP/HTTPS proxy (macOS `networksetup`, Windows registry, Linux `gsettings`)
- 📊 **Dashboard** — web UI at `http://localhost:9998`
- 📦 **One-click build** — PyInstaller scripts for macOS and Windows

## Quick Start

```bash
cd desktop
pip install -r requirements.txt
python app.py
```

> On headless Linux the tray icon won't render, but the proxy and dashboard still start.

## Build for macOS

```bash
pip install -r requirements.txt
python build_mac.py
# Output: dist/AFP (standalone .app bundle)
```

## Build for Windows

```bash
pip install -r requirements.txt
python build_win.py
# Output: dist/AFP.exe
```

## Configuration

Config is stored at `~/.afp/config.json`. Defaults:

| Setting | Default | Description |
|---------|---------|-------------|
| `proxy_port` | 9999 | AFP proxy listen port |
| `dashboard_port` | 9998 | Dashboard web UI port |
| `rules_source` | `"community"` | Rule set: `core`, `community`, or URL |
| `auto_start_proxy` | `true` | Start proxy on launch |
| `auto_set_system_proxy` | `true` | Configure OS proxy automatically |
| `scan_interval_seconds` | 300 | Agent re-scan interval |

## Architecture

```
app.py            → Main entry point, orchestrates all components
tray.py           → pystray-based system tray icon & menu
agent_scanner.py  → Detects running AI agents via process list & config dirs
proxy_manager.py  → OS-specific proxy configuration (macOS/Windows/Linux)
config.py         → Dataclass config with JSON persistence
build_mac.py      → PyInstaller build script for macOS
build_win.py      → PyInstaller build script for Windows
```
