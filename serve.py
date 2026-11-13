#!/usr/bin/env python3
"""Serve the CPE Auto-Healing dashboard (index.html) on the internal network.

Usage:  python3 serve.py [port]      (default port: 13002)
"""
import os
import sys
import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 13002
PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self, head_only=False):
        if self.path.split("?")[0] not in ("/", "/index.html"):
            self.send_error(404)
            return
        # Re-read on each request so replacing index.html needs no restart.
        with open(PAGE, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET(head_only=True)


class Server(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    # 0.0.0.0 = all IPv4 interfaces (includes 127.0.0.1/localhost and the server's LAN IP).
    httpd = Server(("0.0.0.0", PORT), Handler)
    print("Dashboard a escutar em 0.0.0.0:%d (IPv4). Acede por:" % PORT)
    for host in ("127.0.0.1", "localhost", "0.0.0.0", "<ip-do-servidor>"):
        print("  http://%s:%d/" % (host, PORT))
    print("Ctrl+C para parar")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
