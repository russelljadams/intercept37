"""
FastAPI router for the vulnerability scanner.

WARNING: These endpoints trigger active vulnerability testing.
Only use against systems you have explicit written authorization to test.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from intercept37.scanner.engine import ScannerEngine

logger = logging.getLogger("intercept37.api.scanner")

router = APIRouter(prefix="/api/scanner", tags=["scanner"])

# Shared engine instance — default checks, sensible rate limiting
_engine = ScannerEngine()


@router.post("/scan/{request_id}")
async def scan_request(request_id: int):
    """
    Scan a single captured request for vulnerabilities.

    Runs all configured checks against the specified request and
    saves results to the database.
    """
    results = await _engine.scan_request(request_id)
    return {
        "request_id": request_id,
        "findings": len(results),
        "results": results,
    }


@router.post("/scan-all")
async def scan_all(limit: int = Query(100, ge=1, le=1000)):
    """
    Scan all recent unscanned captured requests.

    Finds requests that have no existing scan results and runs all
    checks against them, up to *limit* requests.
    """
    results = await _engine.scan_all(limit=limit)
    return {
        "scanned_findings": len(results),
        "results": results,
    }


@router.post("/scan-host")
async def scan_host(host: str = Query(..., description="Target hostname to scan")):
    """
    Scan all captured requests for a specific host.

    Runs all checks against every captured request matching the given host.
    """
    if not host:
        raise HTTPException(status_code=400, detail="host parameter is required")
    results = await _engine.scan_host(host=host)
    return {
        "host": host,
        "findings": len(results),
        "results": results,
    }
