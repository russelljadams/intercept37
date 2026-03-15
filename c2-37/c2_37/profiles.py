"""c2-37 traffic profiles — malleable C2 communication.

Defines how C2 traffic looks on the wire. Profiles shape HTTP
requests/responses to mimic legitimate traffic patterns.
"""
from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass, field


@dataclass
class C2Profile:
    """Traffic profile that shapes how C2 comms look on the wire."""
    name: str
    description: str

    # Request shaping
    useragent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    headers: dict[str, str] = field(default_factory=dict)

    # URL patterns (server maps these to actual endpoints)
    register_uri: str = "/register"
    beacon_uri: str = "/beacon"
    result_uri: str = "/result"
    stage_uri: str = "/stage"

    # Response shaping
    content_type: str = "application/json"
    prepend: str = ""  # prepend to response body
    append: str = ""   # append to response body

    # Junk parameters to add to URLs
    junk_params: bool = False

    def get_headers(self) -> dict[str, str]:
        """Get request headers for this profile."""
        h = {"User-Agent": self.useragent}
        h.update(self.headers)
        return h

    def shape_url(self, base_url: str, path: str) -> str:
        """Shape a URL according to the profile."""
        url = f"{base_url}{path}"
        if self.junk_params:
            param = ''.join(random.choices(string.ascii_lowercase, k=5))
            val = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            sep = "&" if "?" in url else "?"
            url += f"{sep}{param}={val}"
        return url

    def wrap_response(self, data: bytes) -> bytes:
        """Wrap response data according to profile."""
        result = b""
        if self.prepend:
            result += self.prepend.encode()
        result += data
        if self.append:
            result += self.append.encode()
        return result

    def unwrap_response(self, data: bytes) -> bytes:
        """Unwrap response data according to profile."""
        if self.prepend:
            data = data[len(self.prepend):]
        if self.append:
            data = data[:-len(self.append)]
        return data

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "useragent": self.useragent,
            "uris": {
                "register": self.register_uri,
                "beacon": self.beacon_uri,
                "result": self.result_uri,
                "stage": self.stage_uri,
            },
        }


# ── Built-in profiles ─────────────────────────────────────

PROFILES: dict[str, C2Profile] = {}


def _register(profile: C2Profile):
    PROFILES[profile.name] = profile
    return profile


# Default — plain JSON, standard paths
_register(C2Profile(
    name="default",
    description="Plain JSON — no traffic shaping",
))

# jQuery — disguise as jQuery CDN traffic
_register(C2Profile(
    name="jquery",
    description="Mimic jQuery CDN requests",
    useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    headers={
        "Accept": "text/javascript, application/javascript, */*",
        "Referer": "https://code.jquery.com/",
    },
    register_uri="/jquery-3.7.1.min.js",
    beacon_uri="/jquery-3.7.1.slim.min.js",
    result_uri="/jquery-migrate-3.4.1.min.js",
    stage_uri="/jquery-ui-1.13.2.min.js",
    content_type="application/javascript",
    prepend="/*! jQuery v3.7.1 | (c) OpenJS Foundation | jquery.org/license */\n",
    append="\n//# sourceMappingURL=jquery-3.7.1.min.map",
    junk_params=True,
))

# WordPress — disguise as WP admin AJAX
_register(C2Profile(
    name="wordpress",
    description="Mimic WordPress admin-ajax.php requests",
    useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    headers={
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "/wp-admin/admin.php",
    },
    register_uri="/wp-admin/admin-ajax.php?action=heartbeat",
    beacon_uri="/wp-admin/admin-ajax.php?action=wp_ajax_heartbeat",
    result_uri="/wp-admin/admin-ajax.php?action=save_post",
    stage_uri="/wp-includes/js/wp-embed.min.js",
    content_type="application/json",
))

# API — disguise as REST API traffic
_register(C2Profile(
    name="api",
    description="Mimic generic REST API",
    useragent="python-requests/2.31.0",
    headers={
        "Accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    },
    register_uri="/api/v2/auth/login",
    beacon_uri="/api/v2/notifications/poll",
    result_uri="/api/v2/analytics/events",
    stage_uri="/api/v2/config/bootstrap.js",
    content_type="application/json",
    junk_params=True,
))

# Slack — disguise as Slack webhook traffic
_register(C2Profile(
    name="slack",
    description="Mimic Slack API/webhook traffic",
    useragent="Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
    register_uri="/api/auth.test",
    beacon_uri="/api/conversations.history",
    result_uri="/api/chat.postMessage",
    stage_uri="/api/files.upload",
    content_type="application/json",
))


def get_profile(name: str) -> C2Profile:
    """Get a profile by name."""
    return PROFILES.get(name, PROFILES["default"])


def list_profiles() -> list[dict]:
    """List all available profiles."""
    return [p.to_json() for p in PROFILES.values()]
