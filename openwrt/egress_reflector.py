"""Read-only public-egress probe design; never grants automatic benchmark approval.

An HTTPS reflector at a trusted origin observes the source IP of the HTTPS
request, not the CDN target's route. This report must not be promoted to
egress_contract v1. The caller supplies an explicit local source address only
if it has independently verified that PBR routes use that interface.
"""
import http.client
import ipaddress
import json
import ssl
import time
from urllib.parse import urlsplit

def inspect_reflector(url):
    parsed=urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("HTTPS reflector URL required")
    if parsed.port not in (None,443) or parsed.query or parsed.path not in ("","/ip"):
        raise ValueError("unapproved reflector URL shape")
    if parsed.hostname not in ("api.ipify.org",):
        raise ValueError("reflector must be allowlisted")
    return parsed.hostname

def probe(url, *, timeout=3.0, connector=None):
    host=inspect_reflector(url)
    if not 0 < timeout <= 30:
        raise ValueError("invalid timeout")
    client=connector(host,timeout=timeout) if connector else http.client.HTTPSConnection(host,timeout=timeout,context=ssl.create_default_context())
    try:
        client.request("GET","/ip",headers={"Accept":"text/plain","Connection":"close"})
        response=client.getresponse()
        if response.status != 200:
            raise ValueError("reflector HTTP failure")
        length=response.getheader("Content-Length")
        if length is not None and (not length.isdecimal() or int(length)>64):
            raise ValueError("oversized reflector response")
        data=response.read(65)
        if len(data)>64:
            raise ValueError("oversized reflector response")
        addr=ipaddress.ip_address(data.decode("ascii").strip())
        if addr.version!=4 or not addr.is_global:
            raise ValueError("unusable public egress")
        return {"observed_epoch":time.time(),"egress_ip":str(addr),
                "reflector":host,"read_only":True,
                "target_path_verified":False,"safe_to_apply":False}
    finally:
        client.close()
