"""AI-powered traffic analysis engine using the Anthropic Claude API."""
import json
import logging
import os
from typing import Optional

from anthropic import AsyncAnthropic

from intercept37.llm.prompts import (
    SECURITY_ANALYST_SYSTEM,
    REQUEST_ANALYSIS_PROMPT,
    SESSION_ANALYSIS_PROMPT,
    PAYLOAD_SUGGESTION_PROMPT,
    REPORT_GENERATION_PROMPT,
    EXPLAIN_REQUEST_PROMPT,
)

logger = logging.getLogger("intercept37.llm")


class LLMAnalyzer:
    """Claude-backed security analysis for intercepted HTTP traffic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY or pass api_key."
            )
        self.model = model
        self.client = AsyncAnthropic(api_key=self.api_key)
        # Cumulative token counters for the lifetime of this instance
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _chat(self, user_prompt: str, max_tokens: int = 4096) -> str:
        """Send a single user message with the security analyst system prompt."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=SECURITY_ANALYST_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens
            return response.content[0].text
        except Exception as exc:
            logger.error("LLM API call failed: %s", exc)
            raise

    @staticmethod
    def _truncate(text: Optional[str], limit: int = 2000) -> str:
        if not text:
            return ""
        return text[:limit]

    @staticmethod
    def _parse_json(text: str) -> dict | list:
        """Extract JSON from a response that might be wrapped in markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Strip ```json ... ``` wrapper
            lines = cleaned.split("\n")
            lines = lines[1:]  # drop opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    def _format_request(self, req: dict) -> dict:
        """Produce a standard set of template variables from a request dict."""
        url = req.get("url") or "{scheme}://{host}{path}".format(scheme=req.get("scheme", "http"), host=req.get("host", "unknown"), path=req.get("path", "/"))
        if req.get("query"):
            url += f"?{req[query]}"
        return {
            "method": req.get("method", "GET"),
            "url": url,
            "request_headers": self._truncate(req.get("request_headers", ""), 3000),
            "request_body": self._truncate(req.get("request_body", "")),
            "status_code": req.get("status_code", "N/A"),
            "response_headers": self._truncate(req.get("response_headers", ""), 3000),
            "response_body": self._truncate(req.get("response_body", "")),
            "content_type": req.get("content_type", "unknown"),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_request(self, request: dict) -> dict:
        """Analyze a single request/response for security issues.

        Returns ``{findings: [...], risk_level: str, summary: str}``.
        """
        fmted = self._format_request(request)
        prompt = REQUEST_ANALYSIS_PROMPT.format(**fmted)
        raw = await self._chat(prompt)
        try:
            result = self._parse_json(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON; returning raw text.")
            result = {
                "findings": [],
                "risk_level": "unknown",
                "summary": raw,
            }
        return result

    async def explain_request(self, request: dict) -> str:
        """Explain what a request does in plain English."""
        fmted = self._format_request(request)
        prompt = EXPLAIN_REQUEST_PROMPT.format(**fmted)
        return await self._chat(prompt, max_tokens=2048)

    async def suggest_payloads(self, request: dict, vuln_type: str) -> list[str]:
        """Suggest test payloads for a specific vulnerability type.

        Returns a list of payload dicts (or raw payload strings on parse
        failure).
        """
        fmted = self._format_request(request)
        fmted["vuln_type"] = vuln_type
        prompt = PAYLOAD_SUGGESTION_PROMPT.format(**fmted)
        raw = await self._chat(prompt)
        try:
            return self._parse_json(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse payload JSON; returning raw text.")
            return [{"payload": raw, "target": "unknown", "technique": "unknown",
                      "description": "Raw LLM response (parse failed)", "encoding": "none"}]

    async def analyze_session(self, requests: list[dict]) -> dict:
        """Analyze a series of requests for session-level patterns."""
        if not requests:
            return {"session_findings": [], "risk_level": "none",
                    "summary": "No requests provided."}

        host = requests[0].get("host", "unknown")
        lines: list[str] = []
        for i, req in enumerate(requests):
            fmted = self._format_request(req)
            lines.append(
                f"--- Request #{i + 1} ---\n"
                f"{fmted[method]} {fmted[url]}\n"
                f"Headers: {fmted[request_headers]}\n"
                f"Body: {fmted[request_body]}\n"
                f"Response Status: {fmted[status_code]}\n"
                f"Response Headers: {fmted[response_headers]}\n"
                f"Response Body: {self._truncate(fmted[response_body], 1000)}\n"
            )
        requests_text = "\n".join(lines)
        prompt = SESSION_ANALYSIS_PROMPT.format(
            count=len(requests), host=host, requests_text=requests_text,
        )
        raw = await self._chat(prompt, max_tokens=4096)
        try:
            return self._parse_json(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse session JSON; returning raw text.")
            return {"session_findings": [], "risk_level": "unknown",
                    "summary": raw}

    async def generate_report(
        self, scan_results: list[dict], requests: list[dict],
    ) -> str:
        """Generate a Markdown penetration test report."""
        scan_text = json.dumps(scan_results, indent=2, default=str)[:8000]
        req_lines: list[str] = []
        for i, req in enumerate(requests[:30]):
            fmted = self._format_request(req)
            req_lines.append(
                f"#{i + 1}  {fmted[method]} {fmted[url]}  -> {fmted[status_code]}"
            )
        requests_text = "\n".join(req_lines)

        prompt = REPORT_GENERATION_PROMPT.format(
            vuln_count=len(scan_results),
            scan_results_text=scan_text,
            request_count=len(requests),
            requests_text=requests_text,
        )
        return await self._chat(prompt, max_tokens=8192)

    def get_usage(self) -> dict:
        """Return cumulative token usage."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }
