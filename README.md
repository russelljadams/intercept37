# intercept37

> Open-source intercepting proxy & pentest suite — built for humans and LLMs.

A free, open-source alternative to Burp Suite designed from the ground up with AI/LLM integration. Features an alien-themed web dashboard for human operators and structured API/MCP interfaces for AI-assisted penetration testing.

## Features

### Intercepting Proxy
- HTTP/HTTPS man-in-the-middle proxy (mitmproxy-based)
- Real-time traffic capture & display via WebSocket
- Full request/response inspection

### Web Dashboard
- Alien tech-themed dark UI with live traffic table
- Request inspector with headers, body, syntax highlighting
- Built-in repeater for crafting & replaying requests
- Vulnerability scanner results with severity filtering
- Dashboard stats with method distribution & host tracking

### Vulnerability Scanner
- SQL Injection (error-based + time-based)
- Cross-Site Scripting (XSS)
- Command Injection
- Path Traversal
- SSRF (Server-Side Request Forgery)
- Open Redirect
- Security Header Analysis

### AI-Powered Analysis (Claude Integration)
- Automated security analysis of captured requests
- Plain English request explanations
- Context-aware payload suggestions
- Session-level pattern analysis
- Automated pentest report generation

## Quick Start

```bash
# Clone
git clone https://github.com/russelljadams/intercept37.git
cd intercept37

# Install Python dependencies
pip install -e .

# Build the dashboard
cd frontend && npm install && npm run build && cd ..

# Set your Anthropic API key (optional, for AI features)
export ANTHROPIC_API_KEY=your-key-here

# Launch
intercept37 start
```

Then open http://localhost:1337 for the dashboard and configure your browser/tool to proxy through localhost:8080.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Web Dashboard   │◄──►│  FastAPI Backend   │◄──►│  Proxy Core      │
│  (React/Vite)    │     │  REST + WebSocket  │     │  (mitmproxy)     │
└─────────────────┘     └────────┬───────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────┴─────┐ ┌───┴────┐ ┌─────┴─────┐
              │  Scanner   │ │  LLM   │ │  SQLite   │
              │  Engine    │ │  Layer │ │  Storage  │
              └───────────┘ └────────┘ └───────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/requests` | GET | List captured requests (filterable) |
| `/api/requests/{id}` | GET | Get request details |
| `/api/requests/{id}/repeat` | POST | Replay a request |
| `/api/requests/send` | POST | Send a manual request |
| `/api/stats` | GET | Dashboard statistics |
| `/api/scanner/scan/{id}` | POST | Scan a specific request |
| `/api/scanner/scan-all` | POST | Scan all unscanned requests |
| `/api/scanner/scan-host` | POST | Scan requests by host |
| `/api/scan-results` | GET | List scan results |
| `/api/llm/analyze/{id}` | POST | AI security analysis |
| `/api/llm/explain/{id}` | POST | Plain English explanation |
| `/api/llm/suggest-payloads/{id}` | POST | AI payload suggestions |
| `/api/llm/analyze-session` | POST | Session-level AI analysis |
| `/api/llm/report` | POST | Generate pentest report |
| `/ws` | WebSocket | Real-time traffic stream |

## Tech Stack

- **Python 3.11+** — Backend & proxy
- **mitmproxy** — Proxy engine
- **FastAPI** — REST API + WebSocket server
- **SQLAlchemy + SQLite** — Traffic storage
- **React + TypeScript + Vite** — Dashboard
- **Tailwind CSS** — Alien-themed styling
- **Anthropic Claude API** — AI analysis

## For LLMs / AI Agents

intercept37 is designed to be driven programmatically. All functionality is accessible via REST API with JSON responses. Point your AI agent at the API endpoints above to:
- Capture and analyze web traffic
- Run automated vulnerability scans
- Get AI-powered security insights
- Generate pentest reports

## License

MIT

## Disclaimer

This tool is intended for **authorized security testing only**. Always obtain proper authorization before testing any system you do not own.
