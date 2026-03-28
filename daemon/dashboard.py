"""AFP Web Dashboard — serves UI + JSON APIs."""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from dataclasses import asdict

from logger import AFPLogger

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# Set by cli.py
logger: AFPLogger | None = None
firewall = None  # type: ignore


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif self.path == "/api/events":
            self._json_response(logger.get_events() if logger else [])
        elif self.path == "/api/stats":
            self._json_response(logger.get_stats() if logger else {})
        elif self.path == "/api/rules":
            rules = []
            if firewall and hasattr(firewall, "_rules"):
                rules = [asdict(r) for r in firewall._rules]
            self._json_response(rules)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, name, content_type):
        path = os.path.join(STATIC_DIR, name)
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def start_dashboard(host: str = "127.0.0.1", port: int = 9998) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
