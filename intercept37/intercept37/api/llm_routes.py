"""FastAPI router for LLM-powered analysis endpoints."""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from intercept37.db import get_db
from intercept37.llm.analyzer import LLMAnalyzer
from intercept37.models import CapturedRequest, ScanResult

logger = logging.getLogger("intercept37.api.llm")
router = APIRouter(prefix="/api/llm", tags=["llm"])

# ---------------------------------------------------------------------------
# Shared state — single analyzer instance (lazy-init)
# ---------------------------------------------------------------------------
_analyzer: Optional[LLMAnalyzer] = None


def _get_analyzer() -> LLMAnalyzer:
    """Return a cached LLMAnalyzer, creating one on first use."""
    global _analyzer
    if _analyzer is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise _missing_key_error()
        _analyzer = LLMAnalyzer(api_key=api_key)
    return _analyzer


class _MissingKeyError(Exception):
    pass


def _missing_key_error() -> _MissingKeyError:
    return _MissingKeyError(
        "ANTHROPIC_API_KEY is not set. Export it in your shell or .env file."
    )


def _req_to_dict(req: CapturedRequest) -> dict:
    return req.to_dict()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SessionAnalysisRequest(BaseModel):
    host: str
    limit: int = 50


class ReportRequest(BaseModel):
    host: Optional[str] = None
    limit: int = 100


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status")
def llm_status():
    """Check whether the Anthropic API key is configured."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    configured = bool(key)
    info: dict = {"configured": configured}
    if configured:
        info["model"] = "claude-sonnet-4-20250514"
        info["key_prefix"] = key[:8] + "..."  # safe preview
        if _analyzer is not None:
            info["usage"] = _analyzer.get_usage()
    else:
        info["message"] = (
            "Set the ANTHROPIC_API_KEY environment variable to enable AI analysis."
        )
    return info


@router.post("/analyze/{request_id}")
async def analyze_request(request_id: int, db: Session = Depends(get_db)):
    """AI analysis of a captured request."""
    try:
        analyzer = _get_analyzer()
    except _MissingKeyError as exc:
        return {"error": str(exc)}, 503

    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Request not found"}, 404

    try:
        result = await analyzer.analyze_request(_req_to_dict(req))
        return {"request_id": request_id, "analysis": result}
    except Exception as exc:
        logger.exception("analyze_request failed")
        return {"error": f"Analysis failed: {exc}"}, 500


@router.post("/explain/{request_id}")
async def explain_request(request_id: int, db: Session = Depends(get_db)):
    """Plain-English explanation of a captured request."""
    try:
        analyzer = _get_analyzer()
    except _MissingKeyError as exc:
        return {"error": str(exc)}, 503

    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Request not found"}, 404

    try:
        explanation = await analyzer.explain_request(_req_to_dict(req))
        return {"request_id": request_id, "explanation": explanation}
    except Exception as exc:
        logger.exception("explain_request failed")
        return {"error": f"Explanation failed: {exc}"}, 500


@router.post("/suggest-payloads/{request_id}")
async def suggest_payloads(
    request_id: int,
    vuln_type: str = Query(..., description="Vulnerability type, e.g. sqli, xss, ssti, cmdi, idor"),
    db: Session = Depends(get_db),
):
    """Suggest test payloads for a given vulnerability type."""
    try:
        analyzer = _get_analyzer()
    except _MissingKeyError as exc:
        return {"error": str(exc)}, 503

    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Request not found"}, 404

    try:
        payloads = await analyzer.suggest_payloads(_req_to_dict(req), vuln_type)
        return {"request_id": request_id, "vuln_type": vuln_type, "payloads": payloads}
    except Exception as exc:
        logger.exception("suggest_payloads failed")
        return {"error": f"Payload suggestion failed: {exc}"}, 500


@router.post("/analyze-session")
async def analyze_session(body: SessionAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze recent requests for a host to find session-level issues."""
    try:
        analyzer = _get_analyzer()
    except _MissingKeyError as exc:
        return {"error": str(exc)}, 503

    requests = (
        db.query(CapturedRequest)
        .filter(CapturedRequest.host.contains(body.host))
        .order_by(CapturedRequest.id.asc())
        .limit(body.limit)
        .all()
    )
    if not requests:
        return {"error": f"No captured requests found for host {body.host}"}, 404

    try:
        result = await analyzer.analyze_session([_req_to_dict(r) for r in requests])
        return {"host": body.host, "request_count": len(requests), "analysis": result}
    except Exception as exc:
        logger.exception("analyze_session failed")
        return {"error": f"Session analysis failed: {exc}"}, 500


@router.post("/report")
async def generate_report(body: ReportRequest, db: Session = Depends(get_db)):
    """Generate a Markdown pentest report from scan results and traffic."""
    try:
        analyzer = _get_analyzer()
    except _MissingKeyError as exc:
        return {"error": str(exc)}, 503

    # Gather scan results
    scan_q = db.query(ScanResult).order_by(ScanResult.id.desc())
    scan_results = [r.to_dict() for r in scan_q.all()]

    # Gather requests (optionally filtered by host)
    req_q = db.query(CapturedRequest).order_by(CapturedRequest.id.desc())
    if body.host:
        req_q = req_q.filter(CapturedRequest.host.contains(body.host))
    requests = [_req_to_dict(r) for r in req_q.limit(body.limit).all()]

    if not scan_results and not requests:
        return {"error": "No data available for report generation."}, 404

    try:
        report_md = await analyzer.generate_report(scan_results, requests)
        return {"report": report_md, "findings_count": len(scan_results),
                "requests_analyzed": len(requests)}
    except Exception as exc:
        logger.exception("generate_report failed")
        return {"error": f"Report generation failed: {exc}"}, 500
