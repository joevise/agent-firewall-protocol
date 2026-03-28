#!/usr/bin/env python3
"""Setup script for the AFP OpenClaw skill."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError


SKILL_DIR = Path(__file__).resolve().parent.parent
SDK_SRC = Path(__file__).resolve().parents[3] / "sdk" / "python" / "src"
LIB_DIR = SKILL_DIR / "lib"
AFP_RULES_URL = "https://raw.githubusercontent.com/joevise/agent-firewall-protocol/main/rules/core/default-rules.yaml"


def install_deps() -> None:
    print("[1/3] Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    print("  ✅ pyyaml installed")


def bundle_sdk() -> None:
    print("[2/3] Bundling AFP SDK...")
    if LIB_DIR.exists():
        shutil.rmtree(LIB_DIR)
    if SDK_SRC.exists():
        shutil.copytree(SDK_SRC, LIB_DIR)
        print(f"  ✅ SDK bundled to {LIB_DIR}")
    else:
        print(f"  ⚠️  SDK source not found at {SDK_SRC}, skill may not work without pip install")


def download_rules() -> None:
    print("[3/3] Downloading latest rules...")
    rules_dir = SKILL_DIR / "rules"
    rules_dir.mkdir(exist_ok=True)
    target = rules_dir / "default-rules.yaml"
    try:
        req = Request(AFP_RULES_URL, headers={"User-Agent": "AFP-Setup/0.1"})
        with urlopen(req, timeout=15) as resp:
            target.write_bytes(resp.read())
        print(f"  ✅ Rules saved to {target}")
    except (URLError, OSError) as e:
        print(f"  ⚠️  Could not download rules: {e}")
        print("  Rules will be loaded from cache on first use")


def main() -> None:
    print("🔥 AFP OpenClaw Skill Setup\n")
    install_deps()
    bundle_sdk()
    download_rules()
    print("\n✅ Setup complete! AFP firewall skill is ready.")
    print(f"   Skill directory: {SKILL_DIR}")


if __name__ == "__main__":
    main()
