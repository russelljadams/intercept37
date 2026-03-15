# recon37

Post-exploitation enumerator. 42 checks across 8 categories. Finds the things sysadmins forgot to lock down — which is most things.

## Install

```bash
cd recon37/
pip install -e .
```

## Usage

```bash
# Enumerate via webshell
recon37 enum --webshell 'http://target/shell.php?cmd={cmd}' --human

# Enumerate via SSH
recon37 enum --ssh user@target --password hunter2 --human

# Enumerate via SSH with key
recon37 enum --ssh user@target --key ~/.ssh/id_rsa --human

# Run locally
recon37 enum --local --human

# Run specific check categories only
recon37 enum --local --checks suid,creds,cron --human

# List all available checks
recon37 checks --human

# Explain mode
recon37 enum --webshell 'http://target/cmd.php?c={cmd}' --explain
```

## Check Categories

| Category   | What it finds |
|------------|---------------|
| `system`   | OS, kernel, architecture, hostname |
| `users`    | passwd, logged-in users, sudo rights |
| `suid`     | SUID/SGID binaries, GTFOBins matches |
| `creds`    | Config files, history files, SSH keys, DB creds |
| `network`  | Interfaces, routes, open ports, iptables |
| `cron`     | Cron jobs, writable cron dirs, systemd timers |
| `docker`   | Docker socket, group membership, containers |
| `writable` | World-writable dirs, writable /etc/ files |

## Features

- **3 access methods** — webshell, SSH, or local execution
- **42 enumeration checks** across 8 categories
- **GTFOBins** — flags known privesc binaries
- **JSON + human output** — machine-readable or color-coded terminal output
- **Selective checks** — run only what you need with `--checks`
- **Explain mode** — preview every command before execution

## Dependencies

httpx, rich, click.
