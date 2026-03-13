"""FastAPI server — REST API + WebSocket for real-time traffic."""
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from intercept37.db import get_db, init_db
from intercept37.models import CapturedRequest, ScanResult

logger = logging.getLogger("intercept37.api")

app = FastAPI(title="intercept37", version="0.1.0", description="Pentest suite API")

# LLM analysis routes
from intercept37.api.llm_routes import router as llm_router
app.include_router(llm_router)

# Scanner routes
from intercept37.api.scanner_routes import router as scanner_router

# Chat agent routes
from intercept37.api.chat_routes import router as chat_router
app.include_router(chat_router)
app.include_router(scanner_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active = [c for c in self.active if c != ws]

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_manager = ConnectionManager()


def proxy_listener(record: dict):
    """Called by the proxy addon when a new request/response is captured."""
    asyncio.get_event_loop().create_task(
        ws_manager.broadcast({"type": "new_request", "data": record})
    )


# --- REST Endpoints ---

@app.get("/api/requests")
def list_requests(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    method: Optional[str] = None,
    host: Optional[str] = None,
    status_code: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List captured requests with filtering."""
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
    results = q.offset(offset).limit(limit).all()
    return {"total": total, "data": [r.to_dict() for r in results], "offset": offset, "limit": limit}


@app.get("/api/requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db)):
    """Get full details of a captured request."""
    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Not found"}, 404
    return req.to_dict()


@app.post("/api/requests/{request_id}/repeat")
async def repeat_request(request_id: int, db: Session = Depends(get_db)):
    """Replay a captured request (repeater functionality)."""
    import httpx

    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Not found"}, 404

    headers = json.loads(req.request_headers) if req.request_headers else {}
    headers.pop("host", None)
    headers.pop("Host", None)

    url = f"{req.scheme}://{req.host}:{req.port}{req.path}"
    if req.query:
        url += f"?{req.query}"

    async with httpx.AsyncClient(verify=False, proxy="http://127.0.0.1:8080") as client:
        resp = await client.request(
            method=req.method,
            url=url,
            headers=headers,
            content=req.request_body,
        )

    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text,
    }


@app.post("/api/requests/{request_id}/tag")
def tag_request(request_id: int, tags: list[str], db: Session = Depends(get_db)):
    """Add tags to a request."""
    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Not found"}, 404
    req.tags = json.dumps(tags)
    db.commit()
    return req.to_dict()


@app.post("/api/requests/{request_id}/note")
def add_note(request_id: int, note: str, db: Session = Depends(get_db)):
    """Add a note to a request."""
    req = db.query(CapturedRequest).filter(CapturedRequest.id == request_id).first()
    if not req:
        return {"error": "Not found"}, 404
    req.notes = note
    db.commit()
    return req.to_dict()


@app.get("/api/scan-results")
def list_scan_results(
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List vulnerability scan results."""
    q = db.query(ScanResult).order_by(ScanResult.id.desc())
    if severity:
        q = q.filter(ScanResult.severity == severity.lower())
    return {"results": [r.to_dict() for r in q.all()]}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard stats."""
    total = db.query(CapturedRequest).count()
    by_method = {}
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
        count = db.query(CapturedRequest).filter(CapturedRequest.method == method).count()
        if count:
            by_method[method] = count

    hosts = (
        db.query(CapturedRequest.host)
        .distinct()
        .limit(50)
        .all()
    )
    vulns = db.query(ScanResult).count()

    recent = (
        db.query(CapturedRequest)
        .order_by(CapturedRequest.id.desc())
        .limit(10)
        .all()
    )

    return {
        "total_requests": total,
        "unique_hosts": len([h[0] for h in hosts]),
        "vulnerabilities_found": vulns,
        "active_connections": len(ws_manager.active),
        "method_distribution": by_method,
        "recent_requests": [r.to_dict() for r in recent],
    }




@app.post("/api/requests/send")
async def send_request(req: dict):
    """Send a manual request (repeater)."""
    import httpx

    headers = req.get("headers", {})
    async with httpx.AsyncClient(verify=False, proxy="http://127.0.0.1:8080") as client:
        resp = await client.request(
            method=req.get("method", "GET"),
            url=req["url"],
            headers=headers,
            content=req.get("body", None),
        )
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text,
        "response_time": resp.elapsed.total_seconds(),
    }

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can send commands via WebSocket if needed
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# --- Static file serving for dashboard ---
import os
from pathlib import Path
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the React dashboard (SPA fallback)."""
    file_path = FRONTEND_DIR / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    index = FRONTEND_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"message": "intercept37 API running. Build frontend with: cd frontend && npm run build"}
