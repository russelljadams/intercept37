"""Core proxy engine wrapping mitmproxy."""
import json
import asyncio
import time
import logging
from typing import Optional, Callable
from mitmproxy import options, http
from mitmproxy.tools.dump import DumpMaster
from intercept37.db import SessionLocal, init_db
from intercept37.models import CapturedRequest

logger = logging.getLogger("intercept37.proxy")


class ProxyAddon:
    """mitmproxy addon that captures traffic and broadcasts to listeners."""

    def __init__(self):
        self.listeners: list[Callable] = []
        self._request_times: dict[str, float] = {}

    def add_listener(self, callback: Callable):
        self.listeners.append(callback)

    def remove_listener(self, callback: Callable):
        self.listeners = [l for l in self.listeners if l != callback]

    def request(self, flow: http.HTTPFlow):
        self._request_times[flow.id] = time.time()

    def response(self, flow: http.HTTPFlow):
        elapsed = time.time() - self._request_times.pop(flow.id, time.time())
        record = self._flow_to_record(flow, elapsed)
        self._save_to_db(record)
        self._notify_listeners(record)

    def _flow_to_record(self, flow: http.HTTPFlow, elapsed: float) -> dict:
        req = flow.request
        resp = flow.response
        return {
            "method": req.method,
            "scheme": req.scheme,
            "host": req.host,
            "port": req.port,
            "path": req.path,
            "query": req.query.urlencode() if req.query else None,
            "request_headers": json.dumps(dict(req.headers)),
            "request_body": req.get_text(strict=False),
            "status_code": resp.status_code if resp else None,
            "response_headers": json.dumps(dict(resp.headers)) if resp else None,
            "response_body": resp.get_text(strict=False) if resp else None,
            "response_time": round(elapsed, 4),
            "content_type": resp.headers.get("content-type", "") if resp else None,
        }

    def _save_to_db(self, record: dict):
        try:
            db = SessionLocal()
            entry = CapturedRequest(**record)
            db.add(entry)
            db.commit()
            record["id"] = entry.id
            record["timestamp"] = entry.timestamp.isoformat()
            db.close()
        except Exception as e:
            logger.error(f"Failed to save request: {e}")

    def _notify_listeners(self, record: dict):
        for listener in self.listeners:
            try:
                listener(record)
            except Exception as e:
                logger.error(f"Listener error: {e}")


class ProxyEngine:
    """Manages the mitmproxy instance."""

    def __init__(self, listen_host: str = "127.0.0.1", listen_port: int = 8080):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.addon = ProxyAddon()
        self.master: Optional[DumpMaster] = None

    async def start(self):
        init_db()
        opts = options.Options(
            listen_host=self.listen_host,
            listen_port=self.listen_port,
            ssl_insecure=True,
        )
        self.master = DumpMaster(opts)
        self.master.addons.add(self.addon)
        logger.info(f"Proxy listening on {self.listen_host}:{self.listen_port}")
        await self.master.run()

    def shutdown(self):
        if self.master:
            self.master.shutdown()
