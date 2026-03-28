"""AFP CLI — start/stop/status/logs/rules."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time

AFP_DIR = os.path.expanduser("~/.afp")
PID_FILE = os.path.join(AFP_DIR, "afp.pid")
LOG_FILE = os.path.join(AFP_DIR, "afp.log")


def cmd_start(args):
    os.makedirs(AFP_DIR, exist_ok=True)

    # Check if already running
    if os.path.exists(PID_FILE):
        try:
            pid = int(open(PID_FILE).read().strip())
            os.kill(pid, 0)
            print(f"AFP daemon already running (PID {pid})")
            return
        except (OSError, ValueError):
            os.remove(PID_FILE)

    # Initialize AFP firewall
    sdk_path = os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python', 'src')
    sys.path.insert(0, os.path.abspath(sdk_path))
    from afp import AgentFirewall

    rules_source = args.rules if hasattr(args, 'rules') and args.rules else "core"
    fw = AgentFirewall(rules=rules_source)

    # Initialize logger
    from logger import AFPLogger
    afp_logger = AFPLogger(max_events=1000, log_file=LOG_FILE)

    # Wire up proxy
    import proxy
    proxy.firewall = fw
    proxy.logger = afp_logger

    # Wire up dashboard
    import dashboard
    dashboard.firewall = fw
    dashboard.logger = afp_logger

    proxy_port = args.proxy_port if hasattr(args, 'proxy_port') else 9999
    dash_port = args.dashboard_port if hasattr(args, 'dashboard_port') else 9998

    proxy_server = proxy.start_proxy("127.0.0.1", proxy_port)
    dash_server = dashboard.start_dashboard("127.0.0.1", dash_port)

    # Write PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    rule_count = len(fw._rules)

    print(f"""
╔══════════════════════════════════════════════╗
║  🛡️  AFP — Agent Firewall Protocol           ║
╠══════════════════════════════════════════════╣
║  Proxy:     http://127.0.0.1:{proxy_port:<5}          ║
║  Dashboard: http://127.0.0.1:{dash_port:<5}          ║
║  Rules:     {rule_count} loaded ({rules_source}){' ' * max(0, 18 - len(str(rule_count)) - len(rules_source))}║
║  PID:       {os.getpid():<33}║
╚══════════════════════════════════════════════╝

Configure your agent:  export HTTP_PROXY=http://127.0.0.1:{proxy_port}
Press Ctrl+C to stop.
""")

    def shutdown(sig, frame):
        print("\nShutting down AFP daemon...")
        proxy_server.shutdown()
        dash_server.shutdown()
        try:
            os.remove(PID_FILE)
        except:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(1)


def cmd_stop(args):
    if not os.path.exists(PID_FILE):
        print("AFP daemon is not running.")
        return
    try:
        pid = int(open(PID_FILE).read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"AFP daemon stopped (PID {pid}).")
        os.remove(PID_FILE)
    except (OSError, ValueError) as e:
        print(f"Error stopping daemon: {e}")
        try:
            os.remove(PID_FILE)
        except:
            pass


def cmd_status(args):
    if not os.path.exists(PID_FILE):
        print("AFP daemon is not running.")
        return
    try:
        pid = int(open(PID_FILE).read().strip())
        os.kill(pid, 0)
        print(f"AFP daemon is running (PID {pid}).")
    except (OSError, ValueError):
        print("AFP daemon is not running (stale PID file).")


def cmd_logs(args):
    if not os.path.exists(LOG_FILE):
        print("No log file found.")
        return
    tail = args.tail if hasattr(args, 'tail') else 20
    with open(LOG_FILE) as f:
        lines = f.readlines()
    for line in lines[-tail:]:
        try:
            evt = json.loads(line)
            status = "✅" if evt.get("allowed") else "❌"
            print(f"{evt.get('timestamp','')} {status} {evt.get('action','')} {evt.get('target','')}")
        except:
            print(line.rstrip())


def cmd_rules(args):
    sdk_path = os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python', 'src')
    sys.path.insert(0, os.path.abspath(sdk_path))
    from afp import AgentFirewall
    fw = AgentFirewall(rules="core")
    if not fw._rules:
        print("No rules loaded.")
        return
    for r in fw._rules:
        print(f"  [{r.severity}] {r.name} ({r.id}) — {r.description}")


def main():
    parser = argparse.ArgumentParser(description="AFP — Agent Firewall Protocol")
    sub = parser.add_subparsers(dest="command")

    p_start = sub.add_parser("start", help="Start the AFP daemon")
    p_start.add_argument("--proxy-port", type=int, default=9999)
    p_start.add_argument("--dashboard-port", type=int, default=9998)
    p_start.add_argument("--rules", default="core", help="Rules source: core, community, or path")
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="Stop the AFP daemon")
    p_stop.set_defaults(func=cmd_stop)

    p_status = sub.add_parser("status", help="Check daemon status")
    p_status.set_defaults(func=cmd_status)

    p_logs = sub.add_parser("logs", help="Show recent logs")
    p_logs.add_argument("--tail", type=int, default=20)
    p_logs.set_defaults(func=cmd_logs)

    p_rules = sub.add_parser("rules", help="List loaded rules")
    p_rules.set_defaults(func=cmd_rules)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
