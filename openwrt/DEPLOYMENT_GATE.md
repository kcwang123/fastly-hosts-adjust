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

## Benchmark sample consistency contract

The diagnostic sampler now records ETag and `X-Cache` classifications when present, rejects mixed ETag representations across paired baseline/candidate samples, rejects mixed known HIT/MISS classifications, and rejects high coefficient of variation above the externally configured `max_sample_cv_percent` threshold (default 35%). An absent ETag or Cache header is still `UNKNOWN` diagnostic data, **not** content or cache equivalence proof. For credible throughput conclusions, object hashes, cache provenance and route-specific egress must also be confirmed. Benchmark JSON schema v2 remains read-only and deliberately does not grant DNS write authority.

Public search found historical records of other GitHub Raw ZIP files with Accept-Ranges and >500 KB Content-Length but **not** reproducible Range, cache and origin guarantees for the exact allowlisted GitHub README. The Twitch fallback avatar is documented as a tiny 70x70 image. Neither currently allowlisted path is certified as a valid 256 KiB throughput object; the runner must keep rejecting undersized samples. No official alternative download object has been verified at the same required CDN hostname. Source reference examples: https://urlscan.io/result/019de4bb-5928-76fb-959c-5c6eaefc030d and https://codepen.io/Qwicksilver/pen/QvNdGL .

## Transaction review limitation

`rewrite_tx.py` records a durable snapshot and checks current values just before mutation, but AdGuard Home offers no atomic compare-and-swap. Between read and delete/add, an external actor may update a rewrite. Recovery uses phases and ownership checks, but ambiguous in-flight writes remain possible across process crash. Do not enable write mode until recovery's phase/intent semantics and external-writer interference are tested and understood; `dry_run=true` remains mandatory.
