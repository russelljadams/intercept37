# probe37

> Open-source intercepting proxy & pentest suite — built for humans and LLMs.

An alternative to Burp Suite designed from the ground up with LLM integration in mind. Features a web dashboard for human operators and a structured API/MCP interface for AI-assisted pentesting.

## Architecture

- **Proxy Core** — mitmproxy-based HTTP/HTTPS intercepting proxy
- **FastAPI Backend** — REST API + WebSocket for real-time traffic
- **Web Dashboard** — React-based UI for traffic inspection, replay, scanning
- **LLM Interface** — MCP server + REST endpoints for AI agents to drive the tool

## Features (Planned)

- [x] Project scaffolding
- [ ] HTTP/HTTPS intercepting proxy
- [ ] Real-time traffic capture & display
- [ ] Request inspection & editing
- [ ] Repeater (craft & resend requests)
- [ ] Automated vulnerability scanner
- [ ] LLM-powered traffic analysis
- [ ] MCP server for Claude Code integration
- [ ] Natural language to payload generation
- [ ] Session management & project saves

## Tech Stack

- **Python 3.11+** — Core proxy & backend
- **FastAPI** — API server
- **mitmproxy** — Proxy engine
- **React + TypeScript** — Web dashboard
- **SQLite** — Traffic storage
- **WebSockets** — Real-time streaming

## License

MIT

