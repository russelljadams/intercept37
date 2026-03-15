# intercept37

Intercepting proxy + vulnerability scanner + AI analyzer. Like Burp Suite, but it actually likes you.

## Install

```bash
cd intercept37/
pip install -e .
```

## Usage

```bash
# Start proxy + dashboard (the whole show)
intercept37 start

# Custom ports
intercept37 start --proxy-port 9090 --api-port 1337

# API server only (no proxy)
intercept37 api-only --port 1337
```

**Default endpoints:**
- Proxy: `http://0.0.0.0:8080`
- Dashboard: `http://0.0.0.0:1337`
- API: `http://0.0.0.0:1337/api/`
- WebSocket: `ws://0.0.0.0:1337/ws`

Point your browser proxy at port 8080. Every request gets captured, stored in SQLite, and streamed to the dashboard via WebSocket. The scanner analyzes captured traffic for vulns. The AI analyzer (Claude) reviews findings so you don't have to stare at raw output like it's 2003.

## Features

- **Intercepting proxy** -- mitmproxy core, captures all HTTP traffic to SQLite
- **Vuln scanner** -- automated checks against captured requests (SQLi, XSS, etc.)
- **AI analysis** -- Claude reviews scan findings and explains them like a senior pentester
- **REST API** -- full JSON API for automation and LLM tool integration
- **WebSocket** -- real-time traffic stream to the dashboard
- **Dashboard** -- web UI at /dashboard

## Dependencies

mitmproxy, FastAPI, uvicorn, SQLAlchemy, aiosqlite, httpx, anthropic, rich, click. See `pyproject.toml`.
