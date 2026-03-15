# breach37

Async HTTP form brute forcer. Faster than hydra for web logins because it doesn't pretend it's 1998.

## Install

```bash
cd breach37/
pip install -e .
```

## Usage

```bash
# Brute force a custom login form
breach37 http-form --url http://target/login --user admin -w rockyou \
  --fail-string "Invalid password" --human

# WordPress (auto-configured — knows the form fields, login path, fail string)
breach37 wordpress --url http://target/blog/ --user admin --human

# Jenkins (same deal)
breach37 jenkins --url http://target:8080/ --user admin --human

# List available presets and wordlist shortcuts
breach37 presets --human

# Explain mode — shows what it'll do without doing it
breach37 wordpress --url http://target/ --user admin --explain
```

## Features

- **Async engine** — 30 concurrent requests by default, adjustable with `-c`
- **Presets** — WordPress, Jenkins, Drupal auto-configured (form fields, fail detection)
- **Custom forms** — any HTTP form with `--fail-string`, `--fail-code`, or `--fail-redirect`
- **Rate limiting** — `-r 0.5` for polite bruting (0.5s delay per worker)
- **Wordlist shortcuts** — `rockyou`, or pass a full path
- **JSON + human output** — pipe to jq or read it like a human
- **Explain mode** — `--explain` tells you the plan before sending a single request

## Dependencies

httpx, rich, click.
