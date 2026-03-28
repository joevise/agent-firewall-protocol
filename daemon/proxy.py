"""AFP HTTP Forward Proxy — intercepts agent traffic, checks against AFP rules."""
from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.request import Request, urlopen
from urllib.error import URLError

from logger import AFPLogger, AFPEvent


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# These are set by cli.py before starting the server
firewall = None  # type: ignore
logger: AFPLogger | None = None


class AFPProxyHandler(BaseHTTPRequestHandler):
    def _check_and_forward(self):
        url = self.path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len else b""

        # Build params for AFP check
        params = {"url": url, "body": body.decode("utf-8", errors="replace")}
        result = firewall.check(action="http_request", params=params)

        event = AFPEvent(
            timestamp=AFPLogger.now(),
            action="http_request",
            target=url,
            allowed=result.allowed,
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            reason=result.reason,
            severity=result.severity,
        )
        if logger:
            logger.log(event)

        if not result.allowed:
            resp = json.dumps({
                "error": "blocked_by_afp",
                "rule": result.rule_name,
                "reason": result.reason,
                "severity": result.severity,
            }).encode()
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        # Forward the request
        try:
            fwd_headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in ("host", "proxy-connection")}
            req = Request(url, data=body or None, headers=fwd_headers, method=self.command)
            with urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("transfer-encoding",):
                        self.send_header(k, v)
                self.end_headers()
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except URLError as e:
            err = f"Upstream error: {e}".encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)

    def do_GET(self):
        self._check_and_forward()

    def do_POST(self):
        self._check_and_forward()

    def do_PUT(self):
        self._check_and_forward()

    def do_DELETE(self):
        self._check_and_forward()

    def do_CONNECT(self):
        host_port = self.path.split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 443

        # Check domain against rules
        params = {"url": f"https://{host}", "body": ""}
        result = firewall.check(action="http_request", params=params)

        event = AFPEvent(
            timestamp=AFPLogger.now(),
            action="https_connect",
            target=self.path,
            allowed=result.allowed,
            rule_id=result.rule_id,
            rule_name=result.rule_name,
            reason=result.reason,
            severity=result.severity,
        )
        if logger:
            logger.log(event)

        if not result.allowed:
            self.send_response(403)
            self.end_headers()
            return

        # Tunnel through
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except Exception:
            self.send_response(502)
            self.end_headers()
            return

        self.send_response(200, "Connection Established")
        self.end_headers()

        conn = self.connection

        def relay(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try: src.close()
                except: pass
                try: dst.close()
                except: pass

        t1 = threading.Thread(target=relay, args=(conn, upstream), daemon=True)
        t2 = threading.Thread(target=relay, args=(upstream, conn), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def log_message(self, format, *args):
        pass  # Suppress default logging


def start_proxy(host: str = "127.0.0.1", port: int = 9999) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), AFPProxyHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
