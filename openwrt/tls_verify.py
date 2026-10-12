"""Direct TLS/SNI verification of candidate Fastly route, without DNS changes."""
import ipaddress
import ssl
import socket
import http.client
from dataclasses import dataclass

SERVICES = {
    "raw.githubusercontent.com": "/github/gitignore/main/README.md",
    "pbs.twimg.com": "/profile_images/1683325380441128960/yRsRRjGO_400x400.jpg",
    "static-cdn.jtvnw.net": "/jtv_user_pictures/xarth/404_user_70x70.png",
}

@dataclass(frozen=True)
class Result:
    domain: str
    ip: str
    verified: bool
    status: int | None = None
    reason: str = ""

def verify(domain, ip, timeout=3.0):
    """TCP connect to candidate IP; verify certificate against original domain."""
    if domain not in SERVICES:
        raise ValueError("unrecognized verification domain")
    addr = ipaddress.ip_address(ip)
    if addr.version != 4 or not addr.is_global:
        raise ValueError("candidate must be public IPv4")
    if not 0 < timeout <= 30:
        raise ValueError("invalid timeout")
    sock = None
    tls = None
    try:
        sock = socket.create_connection((ip, 443), timeout=timeout)
        context = ssl.create_default_context()
        tls = context.wrap_socket(sock, server_hostname=domain)
        sock = None
        tls.settimeout(timeout)
        req = ("HEAD " + SERVICES[domain] + " HTTP/1.1\r\nHost: " + domain +
               "\r\nUser-Agent: openwrt-fastly-optimizer/0.1\r\nConnection: close\r\n\r\n")
        tls.sendall(req.encode("ascii"))
        response = http.client.HTTPResponse(tls)
        response.begin()
        status = response.status
        response.close()
        return Result(domain, ip, 200 <= status < 400, status,
                      "http_status" if status >= 400 else "")
    except (OSError, ssl.SSLError, http.client.HTTPException) as e:
        return Result(domain, ip, False, reason=type(e).__name__)
    finally:
        if tls is not None:
            tls.close()
        if sock is not None:
            sock.close()
