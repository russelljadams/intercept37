# toolkit37

> *"The ships hung in the sky in much the same way that bricks don't."*
> *These tools hang in your network in much the same way that firewalls wish they wouldn't.*

LLM-first offensive security tools. Each installs separately, has zero cross-dependencies, and speaks fluent JSON.

---

## The Arsenal

| Tool | Command | What it does | Dependencies |
|------|---------|--------------|--------------|
| **[intercept37](intercept37/)** | `intercept37` | Intercepting proxy + vuln scanner + AI agent | mitmproxy, FastAPI, Claude API |
| **[breach37](breach37/)** | `breach37` | Async HTTP form brute forcer | httpx, click |
| **[recon37](recon37/)** | `recon37` | Post-exploitation enumerator | httpx, click |
| **[venom37](venom37/)** | `venom37` | Reverse shell generator (16 types) | httpx, click |
| **[c2-37](c2-37/)** | `c37` | Lightweight C2 framework | **zero** (stdlib only) |

---

## Quick Start

Each tool is independently installable:

```bash
# Install just what you need
cd intercept37 && pip install -e .
cd breach37 && pip install -e .
cd recon37 && pip install -e .
cd venom37 && pip install -e .
cd c2-37 && pip install -e .
```

Or install everything:

```bash
for dir in intercept37 breach37 recon37 venom37 c2-37; do
    (cd $dir && pip install -e .)
done
```

---

## LLM-First Design

Every tool follows the same philosophy:

| Feature | What it means |
|---------|---------------|
| **JSON by default** | Structured output. Every tool. Always |
| **`--human` flag** | Rich terminal output when a human is reading |
| **`--explain` flag** | Describes what the tool will do, then exits |
| **Teaching mode** | Results explain *why* findings matter |
| **Python importable** | Use them as libraries in your own tools |
| **Sane defaults** | Minimal required args, presets for common configs |

---

## License

MIT. Hack the planet (legally).

## Disclaimer

These are security testing tools. Use them only on systems you own or have explicit written authorization to test.
