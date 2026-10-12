"""Local-only AdGuard Home rewrite API client.

Authentication is supplied in memory; no credential URLs, logs or persisted tokens.
"""
import base64
import ipaddress
import json
import urllib.error
import urllib.parse
import urllib.request


class AdGuardAPI:
    def __init__(self, base_url, username, password, timeout=8.0, opener=None):
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/") or not parsed.port):
            raise ValueError("AdGuard API must be local HTTP host with explicit port")
        if not username or not password or not 0 < timeout <= 300:
            raise ValueError("invalid AdGuard credentials or timeout")
        self.base_url = f"http://{parsed.hostname}:{parsed.port}"
        self.timeout = timeout
        self.opener = opener or urllib.request.urlopen
        self.auth = "Basic " + base64.b64encode((username + ":" + password).encode()).decode()

    def request(self, endpoint, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": self.auth, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + endpoint, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        try:
            with self.opener(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise RuntimeError("AdGuard API unexpected HTTP status")
                raw = response.read(1048577)
                if len(raw) > 1048576:
                    raise RuntimeError("AdGuard API oversized response")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            raise RuntimeError("AdGuard API HTTP " + str(e.code)) from None
        except urllib.error.URLError:
            raise RuntimeError("AdGuard API connection failed") from None

    def list(self):
        result = self.request("/control/rewrite/list")
        if not isinstance(result, list):
            raise RuntimeError("invalid AdGuard rewrite list")
        return result

    def add(self, domain, answer):
        self.request("/control/rewrite/add", {"domain": domain, "answer": answer})

    def delete(self, domain, answer):
        self.request("/control/rewrite/delete", {"domain": domain, "answer": answer})
