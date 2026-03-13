"""CLI for breach37 — HTTP brute force tool."""
from __future__ import annotations

import asyncio
import json
import sys

import click


@click.group("breach")
def breach_cli():
    """breach37 — HTTP form brute forcer.

    Brute force web login forms with async speed.
    Supports WordPress, Jenkins, Drupal, and custom forms.
    """
    pass


@breach_cli.command("http-form")
@click.option("--url", required=True, help="Login form URL (e.g. http://target/login)")
@click.option("--user", "-u", required=True, help="Username to brute force")
@click.option("--wordlist", "-w", default="rockyou", help="Wordlist name or path (default: rockyou)")
@click.option("--fail-string", "-fs", default=None, help="String that appears on FAILED login")
@click.option("--fail-code", "-fc", default=None, type=int, help="HTTP status code on failed login")
@click.option("--fail-redirect", "-fr", default=None, help="Redirect URL on failed login")
@click.option("--method", "-m", default="POST", type=click.Choice(["POST", "GET"]), help="HTTP method")
@click.option("--username-field", default="username", help="Form field name for username")
@click.option("--password-field", default="password", help="Form field name for password")
@click.option("--concurrency", "-c", default=30, help="Parallel requests (default: 30)")
@click.option("--rate-limit", "-r", default=0.0, help="Delay between requests per worker (seconds)")
@click.option("--timeout", "-t", default=10.0, help="Request timeout in seconds")
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--explain", is_flag=True, help="Explain what the tool will do, then exit")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def http_form(url, user, wordlist, fail_string, fail_code, fail_redirect, method,
              username_field, password_field, concurrency, rate_limit, timeout,
              human, explain, verbose):
    """Brute force a custom HTTP login form."""
    from intercept37.brute.engine import HttpBrute

    bruter = HttpBrute(
        url=url, username=user, wordlist=wordlist,
        fail_string=fail_string, fail_code=fail_code, fail_redirect=fail_redirect,
        method=method, username_field=username_field, password_field=password_field,
        concurrency=concurrency, rate_limit=rate_limit, timeout=timeout, verbose=verbose,
    )

    if explain:
        click.echo(bruter.explain())
        return

    result = asyncio.run(bruter.run())
    if human:
        click.echo(result.to_human())
    else:
        click.echo(result.to_json())

    sys.exit(0 if result.success else 1)


@breach_cli.command("wordpress")
@click.option("--url", required=True, help="WordPress base URL (e.g. http://target/blog/)")
@click.option("--user", "-u", required=True, help="Username to brute force")
@click.option("--wordlist", "-w", default="rockyou", help="Wordlist name or path")
@click.option("--concurrency", "-c", default=30, help="Parallel requests")
@click.option("--rate-limit", "-r", default=0.0, help="Delay between requests per worker")
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--explain", is_flag=True, help="Explain what the tool will do, then exit")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def wordpress(url, user, wordlist, concurrency, rate_limit, human, explain, verbose):
    """Brute force a WordPress login (auto-configured)."""
    from intercept37.brute.engine import HttpBrute

    bruter = HttpBrute(
        url=url, username=user, wordlist=wordlist,
        preset="wordpress", concurrency=concurrency,
        rate_limit=rate_limit, verbose=verbose,
    )

    if explain:
        click.echo(bruter.explain())
        return

    result = asyncio.run(bruter.run())
    if human:
        click.echo(result.to_human())
    else:
        click.echo(result.to_json())

    sys.exit(0 if result.success else 1)


@breach_cli.command("jenkins")
@click.option("--url", required=True, help="Jenkins base URL (e.g. http://target:8080/)")
@click.option("--user", "-u", required=True, help="Username to brute force")
@click.option("--wordlist", "-w", default="rockyou", help="Wordlist name or path")
@click.option("--concurrency", "-c", default=30, help="Parallel requests")
@click.option("--rate-limit", "-r", default=0.0, help="Delay between requests per worker")
@click.option("--human", is_flag=True, help="Human-readable output")
@click.option("--explain", is_flag=True, help="Explain what the tool will do, then exit")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def jenkins(url, user, wordlist, concurrency, rate_limit, human, explain, verbose):
    """Brute force a Jenkins login (auto-configured)."""
    from intercept37.brute.engine import HttpBrute

    bruter = HttpBrute(
        url=url, username=user, wordlist=wordlist,
        preset="jenkins", concurrency=concurrency,
        rate_limit=rate_limit, verbose=verbose,
    )

    if explain:
        click.echo(bruter.explain())
        return

    result = asyncio.run(bruter.run())
    if human:
        click.echo(result.to_human())
    else:
        click.echo(result.to_json())

    sys.exit(0 if result.success else 1)


@breach_cli.command("presets")
@click.option("--human", is_flag=True, help="Human-readable output")
def list_presets(human):
    """List available login form presets."""
    from intercept37.brute.presets import PRESETS, WORDLIST_PATHS

    data = {
        "presets": {k: {"description": v["description"], "login_path": v["login_path"]}
                    for k, v in PRESETS.items()},
        "wordlists": WORDLIST_PATHS,
    }

    if human:
        click.echo("\n  Available Presets:")
        for name, info in PRESETS.items():
            click.echo(f"    {name:12s} — {info['description']}")
        click.echo("\n  Wordlist Shortcuts:")
        for name, path in WORDLIST_PATHS.items():
            click.echo(f"    {name:12s} → {path}")
        click.echo()
    else:
        click.echo(json.dumps(data, indent=2))
