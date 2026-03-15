"""Tool definitions for the intercept37 agentic chat system.

Each tool maps to a capability the Claude agent can invoke: browsing
captured traffic, replaying requests, running the vulnerability scanner,
tagging/annotating, and fetching statistics.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import httpx

from intercept37.db import SessionLocal
from intercept37.models import CapturedRequest, ScanResult
from intercept37.scanner.engine import ScannerEngine

logger = logging.getLogger("intercept37.agent.tools")

# Max chars returned for large text fields to keep tool results manageable.
_BODY_LIMIT = 2000

# All outbound requests route through the intercept37 proxy so traffic
# gets captured in the dashboard automatically.
_PROXY_URL = "http://127.0.0.1:8080"


def _truncate(text: Optional[str], limit: int = _BODY_LIMIT) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more chars]"


def _safe_json(raw: Optional[str]) -> Any:
    """Parse a JSON string, returning the original string on failure."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


# --------------------------------------------------------------------------
# Tool dataclass
# --------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict  # JSON Schema for parameters
    execute: Callable[..., Awaitable[Any]]


# --------------------------------------------------------------------------
# Tool implementations (all async)
# --------------------------------------------------------------------------

async def _list_requests(
    limit: int = 25,
    offset: int = 0,
    method: Optional[str] = None,
    host: Optional[str] = None,
    search: Optional[str] = None,
    status_code: Optional[int] = None,
) -> dict:
    db = SessionLocal()
    try:
        q = db.query(CapturedRequest).order_by(CapturedRequest.id.desc())
        if method:
            q = q.filter(CapturedRequest.method == method.upper())
        if host:
            q = q.filter(CapturedRequest.host.contains(host))
        if status_code:
            q = q.filter(CapturedRequest.status_code == status_code)
        if search:
            q = q.filter(
                CapturedRequest.path.contains(search)
                | CapturedRequest.request_body.contains(search)
                | CapturedRequest.response_body.contains(search)
            )
        total = q.count()
        rows = q.offset(offset).limit(min(limit, 100)).all()
        data = []
        for r in rows:
            data.append({
                "id": r.id,
                "method": r.method,
                "host": r.host,
                "path": r.path,
                "query": r.query,
                "status_code": r.status_code,
                "content_type": r.content_type,
                "response_time": r.response_time,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "tags": _safe_json(r.tags),
                "notes": r.notes,
            })
        return {"total": total, "offset": offset, "limit": limit, "data": data}
    finally:
        db.close()


async def _get_request(request_id: int) -> dict:
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}
        d = req.to_dict()
        # Truncate large bodies
        d["request_body"] = _truncate(d.get("request_body"))
        d["response_body"] = _truncate(d.get("response_body"))
        return d
    finally:
        db.close()


async def _repeat_request(request_id: int) -> dict:
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}

        headers = _safe_json(req.request_headers) or {}
        # Remove hop-by-hop headers
        for h in ("host", "Host", "content-length", "Content-Length",
                   "transfer-encoding", "Transfer-Encoding"):
            headers.pop(h, None)

        url = f"{req.scheme}://{req.host}:{req.port}{req.path}"
        if req.query:
            url += f"?{req.query}"

        async with httpx.AsyncClient(verify=False, timeout=30, proxy=_PROXY_URL) as client:
            resp = await client.request(
                method=req.method,
                url=url,
                headers=headers,
                content=req.request_body,
            )
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": _truncate(resp.text),
            "response_time": resp.elapsed.total_seconds(),
        }
    finally:
        db.close()


async def _send_request(
    method: str,
    url: str,
    headers: Optional[dict] = None,
    body: Optional[str] = None,
) -> dict:
    async with httpx.AsyncClient(verify=False, timeout=30, proxy=_PROXY_URL) as client:
        resp = await client.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            content=body,
        )
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": _truncate(resp.text),
        "response_time": resp.elapsed.total_seconds(),
    }


async def _scan_request(request_id: int) -> dict:
    engine = ScannerEngine()
    results = await engine.scan_request(request_id)
    return {"request_id": request_id, "findings": len(results), "results": results}


async def _scan_host(host: str) -> dict:
    engine = ScannerEngine()
    results = await engine.scan_host(host=host)
    return {"host": host, "findings": len(results), "results": results}


async def _scan_all(limit: int = 50) -> dict:
    engine = ScannerEngine()
    results = await engine.scan_all(limit=limit)
    return {"scanned_findings": len(results), "results": results}


async def _get_scan_results(
    severity: Optional[str] = None,
    request_id: Optional[int] = None,
) -> dict:
    db = SessionLocal()
    try:
        q = db.query(ScanResult).order_by(ScanResult.id.desc())
        if severity:
            q = q.filter(ScanResult.severity == severity.lower())
        if request_id:
            q = q.filter(ScanResult.request_id == request_id)
        rows = q.limit(200).all()
        return {"total": len(rows), "results": [r.to_dict() for r in rows]}
    finally:
        db.close()


async def _tag_request(request_id: int, tags: list[str]) -> dict:
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}
        existing = _safe_json(req.tags) or []
        if isinstance(existing, list):
            merged = list(set(existing + tags))
        else:
            merged = tags
        req.tags = json.dumps(merged)
        db.commit()
        return {"request_id": request_id, "tags": merged}
    finally:
        db.close()


async def _add_note(request_id: int, note: str) -> dict:
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}
        req.notes = note
        db.commit()
        return {"request_id": request_id, "note": note}
    finally:
        db.close()


async def _get_stats() -> dict:
    db = SessionLocal()
    try:
        total = db.query(CapturedRequest).count()
        hosts = db.query(CapturedRequest.host).distinct().all()
        vulns = db.query(ScanResult).count()
        by_method: dict[str, int] = {}
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
            c = db.query(CapturedRequest).filter(CapturedRequest.method == method).count()
            if c:
                by_method[method] = c
        by_severity: dict[str, int] = {}
        for sev in ("critical", "high", "medium", "low", "info"):
            c = db.query(ScanResult).filter(ScanResult.severity == sev).count()
            if c:
                by_severity[sev] = c
        return {
            "total_requests": total,
            "unique_hosts": len(hosts),
            "vulnerabilities_found": vulns,
            "method_distribution": by_method,
            "severity_distribution": by_severity,
        }
    finally:
        db.close()


async def _analyze_request(request_id: int) -> dict:
    """Fetch request data and return it for inline Claude analysis.

    Instead of making a nested Anthropic API call, we return the request
    details with an instruction flag so the chat loop knows Claude should
    analyze it directly.
    """
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}
        d = req.to_dict()
        d["request_body"] = _truncate(d.get("request_body"), 3000)
        d["response_body"] = _truncate(d.get("response_body"), 3000)
        return {
            "_inline_analysis": True,
            "instruction": (
                "Analyze this HTTP request/response for security vulnerabilities. "
                "Consider OWASP Top 10, injection points, auth issues, sensitive data "
                "exposure, header security, cookie flags, and business logic flaws. "
                "Rate severity as critical/high/medium/low/info."
            ),
            "request": d,
        }
    finally:
        db.close()


async def _suggest_payloads(request_id: int, vuln_type: str) -> dict:
    """Return request context for Claude to reason about payloads inline."""
    db = SessionLocal()
    try:
        req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
        if not req:
            return {"error": f"Request {request_id} not found"}
        d = req.to_dict()
        d["request_body"] = _truncate(d.get("request_body"), 3000)
        d["response_body"] = _truncate(d.get("response_body"), 1000)
        return {
            "_inline_analysis": True,
            "instruction": (
                f"Suggest specific test payloads for '{vuln_type}' vulnerabilities "
                "against this request. For each payload, explain the injection point, "
                "the payload string, what it tests, and any encoding needed. "
                "Provide at least 5 practical payloads."
            ),
            "vuln_type": vuln_type,
            "request": d,
        }
    finally:
        db.close()


async def _generate_report(host: Optional[str] = None) -> dict:
    """Gather scan results and request data for Claude to format a report."""
    db = SessionLocal()
    try:
        scan_q = db.query(ScanResult).order_by(ScanResult.id.desc())
        req_q = db.query(CapturedRequest).order_by(CapturedRequest.id.desc())
        if host:
            req_q = req_q.filter(CapturedRequest.host.contains(host))
            # Also filter scan results to only those request_ids
            host_req_ids = [
                r.id for r in db.query(CapturedRequest.id)
                .filter(CapturedRequest.host.contains(host)).all()
            ]
            if host_req_ids:
                scan_q = scan_q.filter(ScanResult.request_id.in_(host_req_ids))
            else:
                scan_q = scan_q.filter(False)  # no results

        scan_results = [r.to_dict() for r in scan_q.limit(200).all()]
        requests = []
        for r in req_q.limit(50).all():
            requests.append({
                "id": r.id,
                "method": r.method,
                "host": r.host,
                "path": r.path,
                "status_code": r.status_code,
                "content_type": r.content_type,
            })

        return {
            "_inline_analysis": True,
            "instruction": (
                "Generate a professional penetration test report in Markdown. "
                "Include: executive summary, methodology, findings sorted by severity, "
                "evidence, remediation recommendations, and a summary table. "
                "Use the scan results and request data provided."
            ),
            "host": host or "all hosts",
            "scan_results": scan_results,
            "requests_summary": requests,
            "total_findings": len(scan_results),
            "total_requests": len(requests),
        }
    finally:
        db.close()


async def _get_proxy_status() -> dict:
    """Check proxy status — basic info about captured traffic."""
    db = SessionLocal()
    try:
        total = db.query(CapturedRequest).count()
        latest = (
            db.query(CapturedRequest)
            .order_by(CapturedRequest.id.desc())
            .first()
        )
        latest_ts = latest.timestamp.isoformat() if latest and latest.timestamp else None
        return {
            "total_captured": total,
            "latest_request_time": latest_ts,
            "database": os.environ.get("PROBE37_DB", "intercept37_data.db"),
        }
    finally:
        db.close()




async def _crawl_target(
    url: str,
    depth: int = 2,
    max_pages: int = 20,
) -> dict:
    """Spider a target URL, following links to discover pages and endpoints."""
    from urllib.parse import urljoin, urlparse
    import re

    visited: set[str] = set()
    results: list[dict] = []
    to_visit: list[tuple[str, int]] = [(url, 0)]
    base_host = urlparse(url).hostname

    async with httpx.AsyncClient(verify=False, timeout=15, follow_redirects=True, proxy=_PROXY_URL) as client:
        while to_visit and len(visited) < max_pages:
            current_url, current_depth = to_visit.pop(0)

            # Normalize
            parsed = urlparse(current_url)
            if parsed.hostname != base_host:
                continue
            normalized = f"{parsed.scheme}://{parsed.hostname}{parsed.path}"
            if normalized in visited:
                continue
            visited.add(normalized)

            try:
                resp = await client.get(current_url)
                results.append({
                    "url": current_url,
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("content-type", ""),
                    "size": len(resp.content),
                })

                # Extract links if HTML and not too deep
                if current_depth < depth and "text/html" in resp.headers.get("content-type", ""):
                    links = re.findall(r'(?:href|src|action)=["\'](.*?)["\'\']', resp.text)
                    for link in links:
                        full = urljoin(current_url, link)
                        full_parsed = urlparse(full)
                        if full_parsed.hostname == base_host and full_parsed.scheme in ("http", "https"):
                            clean = f"{full_parsed.scheme}://{full_parsed.hostname}{full_parsed.path}"
                            if full_parsed.query:
                                clean += f"?{full_parsed.query}"
                            if clean not in visited:
                                to_visit.append((clean, current_depth + 1))
            except Exception as e:
                results.append({"url": current_url, "error": str(e)})

    return {
        "pages_discovered": len(results),
        "results": results,
    }

# --------------------------------------------------------------------------
# Tool registry
# --------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="list_requests",
        description="List and search captured proxy traffic. Returns a summary of intercepted HTTP requests with filtering options.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results to return (default 25, max 100)", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset", "default": 0},
                "method": {"type": "string", "description": "Filter by HTTP method (GET, POST, etc.)"},
                "host": {"type": "string", "description": "Filter by hostname (partial match)"},
                "search": {"type": "string", "description": "Search in path, request body, and response body"},
                "status_code": {"type": "integer", "description": "Filter by response status code"},
            },
            "required": [],
        },
        execute=_list_requests,
    ),
    Tool(
        name="get_request",
        description="Get full details of a specific captured request including headers, body, and response.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the captured request"},
            },
            "required": ["request_id"],
        },
        execute=_get_request,
    ),
    Tool(
        name="repeat_request",
        description="Replay a previously captured request. Sends the same request again and returns the new response.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request to replay"},
            },
            "required": ["request_id"],
        },
        execute=_repeat_request,
    ),
    Tool(
        name="send_request",
        description="Send a custom HTTP request (repeater). Use this to craft and send arbitrary requests for testing.",
        input_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE, etc.)"},
                "url": {"type": "string", "description": "Full URL to send the request to"},
                "headers": {"type": "object", "description": "Request headers as key-value pairs", "additionalProperties": {"type": "string"}},
                "body": {"type": "string", "description": "Request body content"},
            },
            "required": ["method", "url"],
        },
        execute=_send_request,
    ),
    Tool(
        name="scan_request",
        description="Run the automated vulnerability scanner against a specific captured request. Tests for SQLi, XSS, header issues, and more.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request to scan"},
            },
            "required": ["request_id"],
        },
        execute=_scan_request,
    ),
    Tool(
        name="scan_host",
        description="Run the vulnerability scanner against all captured requests for a specific host.",
        input_schema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Target hostname to scan"},
            },
            "required": ["host"],
        },
        execute=_scan_host,
    ),
    Tool(
        name="scan_all",
        description="Scan all unscanned captured requests for vulnerabilities. Use limit to control how many.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max requests to scan (default 50)", "default": 50},
            },
            "required": [],
        },
        execute=_scan_all,
    ),
    Tool(
        name="get_scan_results",
        description="Retrieve vulnerability scan results. Optionally filter by severity or request ID.",
        input_schema={
            "type": "object",
            "properties": {
                "severity": {"type": "string", "description": "Filter by severity: critical, high, medium, low, info"},
                "request_id": {"type": "integer", "description": "Filter results for a specific request"},
            },
            "required": [],
        },
        execute=_get_scan_results,
    ),
    Tool(
        name="tag_request",
        description="Add tags to a captured request for organization. Tags are merged with existing tags.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request to tag"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to add"},
            },
            "required": ["request_id", "tags"],
        },
        execute=_tag_request,
    ),
    Tool(
        name="add_note",
        description="Add a note/annotation to a captured request.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request"},
                "note": {"type": "string", "description": "Note text to attach"},
            },
            "required": ["request_id", "note"],
        },
        execute=_add_note,
    ),
    Tool(
        name="get_stats",
        description="Get dashboard statistics: total requests, unique hosts, vulnerability counts, and distributions.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        execute=_get_stats,
    ),
    Tool(
        name="analyze_request",
        description="Perform a deep security analysis of a captured request. Examines headers, parameters, cookies, response data, and identifies potential vulnerabilities.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request to analyze"},
            },
            "required": ["request_id"],
        },
        execute=_analyze_request,
    ),
    Tool(
        name="suggest_payloads",
        description="Get specific test payload suggestions for a vulnerability type against a captured request. Returns injection points and ready-to-use payloads.",
        input_schema={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer", "description": "ID of the request to generate payloads for"},
                "vuln_type": {"type": "string", "description": "Vulnerability type: sqli, xss, ssti, cmdi, idor, ssrf, lfi, auth_bypass, etc."},
            },
            "required": ["request_id", "vuln_type"],
        },
        execute=_suggest_payloads,
    ),
    Tool(
        name="generate_report",
        description="Generate a professional penetration test report from all scan results and captured traffic data.",
        input_schema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Optional: limit report to a specific host"},
            },
            "required": [],
        },
        execute=_generate_report,
    ),
    Tool(
        name="get_proxy_status",
        description="Check proxy status — total captured requests, latest capture time, and database info.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        execute=_get_proxy_status,
    ),
    Tool(
        name="crawl_target",
        description="Spider/crawl a target URL to discover pages, endpoints, and generate traffic through the proxy. Follows links up to a specified depth. Use this to map out a target application.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Starting URL to crawl (e.g., https://target.com)"},
                "depth": {"type": "integer", "description": "How many levels deep to follow links (default 2)", "default": 2},
                "max_pages": {"type": "integer", "description": "Maximum pages to visit (default 20)", "default": 20},
            },
            "required": ["url"],
        },
        execute=_crawl_target,
    ),
]


def get_tool_schemas() -> list[dict]:
    """Return tool definitions in Anthropic API format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in TOOLS
    ]


def get_tool_by_name(name: str) -> Tool | None:
    """Look up a tool by name, or return None."""
    return next((t for t in TOOLS if t.name == name), None)
