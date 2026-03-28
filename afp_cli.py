#!/usr/bin/env python3
"""AFP — Agent Firewall Protocol daemon entry point."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sdk', 'python', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daemon'))

from cli import main
main()
