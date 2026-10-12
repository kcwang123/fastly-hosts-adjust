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

## CDN object review (2026-10-12)

Current allowlisted probe paths are GitHub `/github/gitignore/main/README.md` (a text README) and Twitch `/jtv_user_pictures/xarth/404_user_70x70.png` (a 70×70 fallback avatar). These are functionally useful for small HTTPS reachability checks, **not representative throughput benchmark objects**. The benchmark correctly rejects a transfer shorter than `benchmark_sample_bytes` (default 262144 bytes). Do not suppress this failure by reducing the sample size merely to achieve a green result. A stable, legally downloadable, cache-characterized large object at the *same hostname and Fastly route* must be independently verified before using throughput comparisons. Any server ignoring Range is limited by local read bounds but its network overhead is not fully accounted for.

## Distinguishing route vs reflector egress

`egress_reflector.py` permits bounded HTTPS observations from an allowlisted reflector, returning `target_path_verified=false`. It **does not** bind the reflector's route to the CDN destination or guarantee equivalent PBR/WARP policy treatment. A convincing per-route verification requires a trusted probe observation associated with each destination IP, verified packet/connection routing policy and consistent independently measured public exit, not merely equal `ip route get` or source IP from an unrelated reflector. Router policy verification is still outstanding; the Runner therefore unconditionally rejects the auto-benchmark branch after inspecting untrusted evidence. It cannot be enabled by a handcrafted JSON or local HMAC.

The existing explicit-target benchmark remains available as a read-only diagnostic. Performance regression cannot trigger a DNS rewrite because no benchmark output has write authorization.
