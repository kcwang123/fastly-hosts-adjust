"""Bounded, read-only HTTPS download benchmark with hostname certificate validation.

Only domain/path pairs from trusted built-in allowlist are accepted.
No DNS rewrite or /etc/hosts mutations. A single shared byte budget is
allocated BEFORE each download to prevent aggregate overrun.
"""
import argparse
import http.client
import ipaddress
import json
import socket
import ssl
import time
from pathlib import Path
from settings import Settings
from speed_contract import check_evidence
from tls_verify import SERVICES


class Budget:
    def __init__(self, maximum):
        if type(maximum) is not int or maximum < 1:
            raise ValueError("invalid budget")
        self.remaining = maximum
        self.used = 0

    def reserve(self, amount):
        if type(amount) is not int or amount < 1 or amount > self.remaining:
            raise ValueError("insufficient byte budget")
        self.remaining -= amount
        return amount

    def finish(self, reserved, actual):
        if actual < 0 or actual > reserved:
            raise ValueError("download exceeded reservation")
        self.used += actual
        self.remaining += reserved - actual


def download(domain, ip, limit, connect_timeout, read_timeout, deadline=None):
    if domain not in SERVICES:
        raise ValueError("unrecognized Fastly hostname")
    address = ipaddress.ip_address(ip)
    if address.version != 4 or not address.is_global:
        raise ValueError("public IPv4 required")
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("benchmark deadline exceeded")
    sock = None
    tls = None
    count = 0
    started = time.monotonic()
    try:
        sock = socket.create_connection((ip, 443), timeout=connect_timeout)
        tls = ssl.create_default_context().wrap_socket(sock, server_hostname=domain)
        sock = None
        tls.settimeout(min(read_timeout, max(0.001, deadline - time.monotonic())) if deadline else read_timeout)
        request = ("GET " + SERVICES[domain] + " HTTP/1.1\r\nHost: " + domain
                   + "\r\nRange: bytes=0-" + str(limit - 1)
                   + "\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n")
        tls.sendall(request.encode("ascii"))
        response = http.client.HTTPResponse(tls)
        response.begin()
        if response.status not in (200, 206):
            raise ValueError("HTTP download status not OK")
        # A server may ignore Range. Never read past the reserved budget.
        while count < limit:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("benchmark deadline exceeded")
                tls.settimeout(min(read_timeout, remaining))
            chunk = response.read(min(16384, limit - count))
            if not chunk:
                break
            count += len(chunk)
        duration = max(time.monotonic() - started, 0.000001)
        if count == 0:
            raise ValueError("empty download")
        return {"bytes": count, "mbps": count * 8 / duration / 1_000_000,
                "status": response.status, "tls_verified": True}
    finally:
        if tls is not None:
            tls.close()
        if sock is not None:
            sock.close()


def benchmark(domain, baseline_ip, candidate_ip, settings, *, sampler=download):
    if settings.benchmark_workers != 1:
        raise ValueError("parallel mode not implemented")
    if baseline_ip == candidate_ip:
        raise ValueError("baseline and candidate IP must differ")
    budget = Budget(settings.max_benchmark_bytes)
    deadline = time.monotonic() + settings.benchmark_deadline_seconds
    samples = {"baseline_mbps": [], "candidate_mbps": []}
    statuses = []
    # Alternate pair order across rounds to reduce systematic bias.
    for round_no in range(settings.benchmark_rounds):
        labels = ("baseline", "candidate") if round_no % 2 == 0 else ("candidate", "baseline")
        for label in labels:
            if time.monotonic() >= deadline:
                raise TimeoutError("benchmark deadline exceeded")
            reserved = budget.reserve(settings.benchmark_sample_bytes)
            ip = baseline_ip if label == "baseline" else candidate_ip
            # Do not refund bytes from a failed/ambiguous transport: charge
            # full reservation to avoid exceeding budget on retries.
            try:
                result = sampler(domain, ip, reserved, settings.connect_timeout_seconds,
                                 settings.benchmark_read_timeout_seconds)
            except Exception:
                budget.finish(reserved, reserved)
                raise
            budget.finish(reserved, result["bytes"])
            if time.monotonic() >= deadline:
                raise TimeoutError("benchmark deadline exceeded")
            if result.get("tls_verified") is not True or result.get("status") not in (200, 206):
                raise ValueError("TLS or HTTP verification failed")
            samples[label + "_mbps"].append(result["mbps"])
            statuses.append(result["status"])
    raw = {"schema_version": 2, "safe_to_apply": False,
           "bytes_downloaded": budget.used,
           "measurements": [{"domain": domain, "ip": candidate_ip,
                             "sni_domain": domain, "tls_verified": True,
                             "http_status": statuses[-1], **samples}]}
    validated = check_evidence(raw, max_bytes=settings.max_benchmark_bytes,
                               min_improvement_percent=settings.min_improvement_percent,
                               minimum_rounds=settings.benchmark_rounds)
    return {"evidence": raw, "evaluation": validated, "dry_run": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--domain", choices=sorted(SERVICES), required=True)
    parser.add_argument("--baseline-ip", required=True)
    parser.add_argument("--candidate-ip", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    settings = Settings.load(args.config)
    if not settings.dry_run:
        raise ValueError("benchmark requires dry_run=true")
    output = benchmark(args.domain, args.baseline_ip, args.candidate_ip, settings)
    Path(args.output).write_text(json.dumps(output["evidence"], indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
