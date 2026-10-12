# Deployment gate — NOT production approved

This change remains **read-only** and a Draft PR. No cron installation, DHCP, dnsmasq, firewall, PBR, WARP or AdGuard Rewrite writes are authorized.

## Automated benchmark gating

`auto_benchmark` defaults to false. Before enabling it in a test environment:

1. Confirm the 3-hour health scan produces fresh latency evidence. Every failed scan must discard stale output.
2. Pin each approved baseline IP; neither system DNS nor AdGuard Home DNS Rewrite is a trusted baseline source.
3. Capture independent route-specific public egress observations (baseline and candidate), each with interface, route, timestamp and the independently probed public IPv4 address. A route dump or a user Boolean alone is **not evidence of the actual public egress**.
4. Provide `egress_evidence_path` (private file under `/etc/fastly-optimizer/`), set `max_egress_age_seconds` (default 3600); the runner rejects stale, missing, mismatched or incomplete evidence.
5. Verify that the AdGuard Rewrite list does not contain a rewrite for any baseline hostname. If it does, auto benchmarking stops.
6. Verify PBR/WARP policy routing, outbound source route and independent external observations on the **actual OpenWrt device**. External evidence may be spoofed; this contract is not cryptographic attestation.
7. Keep `dry_run: true` and `benchmark_workers: 1`. Never infer DNS write authorization from speed evidence (`safe_to_apply: false`).

## Preflight (read-only)

`sh openwrt/deployment_preflight.sh` checks port 53 DNS, port 67 DHCP, dnsmasq port 54, Python stdlib, AdGuard config, and overlay space. It does **not** install anything or prove runtime readiness by itself.

## Blockers

- An independent, trustworthy egress probe that **collects** the required baseline/candidate observations is not implemented. The JSON validator cannot prove authenticity or true same-route behavior.
- HTTPS benchmark endpoints may produce files too small for accurate throughput; actual CDN object selection remains unverified.
- Link-level byte overhead and retransmissions are not included in download-body budget.
- Real OpenWrt CPU/RAM, PBR/WARP, Python packaging, crash recovery and AdGuard integration require device-specific read-only acceptance.
- No production scheduler or DNS mutation is permitted.

## Read-only route observation (new)

The `route_observer.py` CLI accepts only a JSON list of exact `domain`, `baseline_ip`, and `candidate_ip` entries, then executes `ip -4 route get <IP>` for each endpoint. This is diagnostic evidence of the local kernel routing decision, **not a proof of public egress** and cannot be used as the `egress_evidence_path` consumed by the automatic benchmark.

Example (on a staging/test environment only):

```sh
python3 openwrt/route_observer.py --targets /tmp/benchmark-targets.json --output /tmp/route-diagnostics.json --timeout 3
```

The Python `seal`/`verify_seal` helpers support HMAC-SHA256 tamper detection when an independent >=32-byte secret is provided. This only establishes that an envelope was not changed by parties without that key. **It does not establish authenticity of the route data, network exit, or probe implementation.** Never commit this key.

No reliable per-destination public-egress probe or cryptographic external attestation has been implemented. A local `ip route get` or manually constructed JSON must not unblock benchmark automation. Keep `auto_benchmark=false` and `dry_run=true` until a trustworthy verifier is built and end-to-end validated.
