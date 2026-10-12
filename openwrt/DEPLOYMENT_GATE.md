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

## Persisted benchmark envelope (current)

The benchmark CLI writes a read-only JSON envelope containing `evidence`, `evaluation`, `diagnostics` (CV, ETag and cache state), and `dry_run=true`. Runner checks that the envelope exists, that diagnostics have bounded values, and that the evaluation is consistent with the validated speed evidence. Evidence cannot authorize a DNS rewrite. An older raw schema-v2-only file fails closed rather than silently dropping diagnostics.

This does not independently recompute CV or ETag parity from raw rounds: schema v2 contains only speed arrays, not per-sample response headers. A future v3 contract should carry all observations so Runner can recompute consistency instead of trusting diagnostic summaries. Files are local, unsigned diagnostics; absent/mixed origin Cache and ETag remain weak evidence.

## Read-only object inspection

As of 2026-10-12, `raw.githubusercontent.com/github/gitignore/main/README.md` serves a short text README and `static-cdn.jtvnw.net/jtv_user_pictures/xarth/404_user_70x70.png` serves a small avatar. These resources are unsuitable for the configured 262144-byte throughput sample. The read-only web fetch does not expose reproducible CDN-node-specific `Range`, `Content-Length`, `ETag`, or Cache HIT/MISS response headers. No alternate GitHub or Twitch object has been approved. Keep the benchmark source gate closed.

## Transaction fault injection

Added isolated API fixtures for a concurrent external writer before DNS mutation and for recovery when the live entry differs from both prior and desired values. Both fail closed; the journal is preserved for manual reconciliation. This is **not** proof of atomicity: AdGuard's delete/add sequence still lacks an API CAS operation, and a racing external change after our read remains possible. No production DNS write has been performed.

## Schema v3 verification and compatibility (2026-10-12)

Benchmark CLI now emits a v3 envelope with each measured round's label, domain/IP/SNI, TLS and HTTP status, ETag, X-Cache class, Content-Range, Content-Length, body bytes, elapsed seconds and Mbps. The Runner uses `benchmark_v3.verify` to **recompute** throughput, CV, content/cache consistency, sampled byte budget, target pairing and schema-v2-compatible `evaluation` rather than trusting diagnostic summaries. A legacy v2 object remains accepted by `speed_contract.check_evidence` only as a read-only historic report; **Runner rejects v2 for new success timestamps**.

The local v3 record is still not independent proof of remote server identity, actual per-route public egress, or received body *content equivalence*: matching ETags depend on origin semantics and absence of validators remains inconclusive. A stable, large GitHub/Twitch CDN object is still NOT APPROVED. The certificate/SNI and header parser checks are necessary but insufficient to authorize DNS changes.

## DNS recovery phase restrictions

Recovery now accepts only the known `prepared`, `applying` and `committing` journal phases. An unexpected or absent phase is refused. Since no local DNS API write should have occurred in `prepared`, any live divergence from the prepared snapshot is treated as an external change and fails closed, preserving the journal. Tests cover the post-delete/pre-add crash and the external modification of a prepared journal. API delete/add still has no CAS guarantee, so production writes remain prohibited.

## Isolated TLS-to-Runner acceptance (2026-10-12)

A test now starts a loopback TLS endpoint with a temporary SAN certificate and serves six 206 responses with exact Content-Range, Content-Length, consistent ETag and X-Cache. It invokes the actual `https_benchmark.main` CLI code under injected loopback sockets, writes the v3 JSON envelope and has Runner independently load and verify its per-round samples. No public network or router services are contacted. This is an in-process CLI invocation under controlled socket injection, not an OS-spawned subprocess or a production CDN acceptance test.

The test mutates ETag data after persistence and confirms `benchmark_v3.verify` rejects the altered record. Independent tests cover missing/duplicate rounds, mismatched target pairs, inconsistent elapsed time/CV/cache and a multi-target byte budget. Do not interpret a green CI as proof of route authenticity or real CDN throughput.

## Transaction durability fault injections

Isolated test doubles simulate fsync failure, atomic rename failure, API delete succeeding before subsequent add fails, and ownership registry commit errors. A partial API delete with no successful add is **ambiguous** because an external writer could also have removed the rewrite. The code retains its durable journal, fails closed and requires explicit recovery; it deliberately does not claim to have rolled back that ambiguous state automatically. The test does not grant permission for a live AdGuard rewrite. Absence of compare-and-swap means atomicity remains unproven.

## True OS subprocess acceptance and remaining transaction gates (2026-10-12)

The isolated `test_openwrt_v3_os_subprocess.py` invokes the actual `https_benchmark.py` in a separate Python OS process, using a temporary `sitecustomize.py` injected **only into that child** to redirect TCP 443 connections to a controlled local TLS server; the child validates the ephemeral test certificate with `SSL_CERT_FILE`. Runner unlinks a pre-existing invalid output before execution and reads only the new v3 artifact. The test verifies six real TLS/HTTP Range samples and the unchanged read-only evidence state. This is not a real CDN or PBR/WARP acceptance test.

Additional Runner tests confirm a stale artifact left by an executor reporting return code 0 is never reused and that a timeout cannot advance an existing state timestamp. Earlier v3 unit tests cover metadata, elapsed-time, CV, ETag, Cache and target-IP tampering, and multi-target budget boundaries.

Isolated transaction tests already cover `prepared` / `applying` / `committing` recovery branches, lost API write replies, external rewrite drift, journal durability, rename/fsync failure and delete success followed by add failure. No atomic compare-and-swap is available from the current AdGuard Rewrite API flow. These checks do not close a race where a different writer changes an entry between our read and our next API write; therefore **do not authorize write mode**. Real CDN throughput objects and real router preflight remain unapproved.

## Scheduler freshness and multi-target failure (2026-10-12)

A successful *manual configured* benchmark no longer updates `last_health_epoch`: it did not execute the health scanner. Its timestamp remains unchanged/absent, so a health scan can still become due independently. Added two-target runner fault tests showing that malformed first-child v3 output, a timeout, and previously existing benchmark artifacts cannot advance benchmark state. The earlier real TLS OS-subprocess E2E is still single-target; a full multi-target OS-subprocess TLS acceptance run remains outstanding.

## Write-path risk remains blocking

The AdGuard Home owned-only transaction has durable prepared/applying/committing journal transitions and isolation tests for fsync, rename, partial delete/add, registry commit, and external changes. These are not atomic compare-and-swap operations: read-before-write checks leave a race and recovered state can be ambiguous. No live DNS write, Router deployment or scheduler enablement is authorized. No validated high-volume GitHub/Twitch Fastly benchmark object or destination-bound WARP/PBR egress attestation has been obtained.

## Two-target actual subprocess and scheduling audit — 2026-10-12

Isolated `test_openwrt_v3_two_target_os_process.py` runs two *separate OS child processes* against a loopback TLS server with a temporary two-hostname SAN certificate. It observes 12 actual TLS Range requests, each target producing six v3 samples and 768 body bytes, within the configured 1536-byte aggregate budget. Both envelopes are independently validated by Runner, with a single benchmark timestamp and no health timestamp. The subprocess connection is redirected only by a temporary Python `sitecustomize` injected into test children. This is not production routing or live CDN certification.

Runner's first-run mode contract remains: no explicit benchmark targets => health scan; explicit configured manual diagnostic targets => benchmark; automatic mode with no prior health => health first. Health and benchmark timestamps are independent; absence of a configured benchmark leaves benchmark_pending after health is fresh. New isolation tests cover these due-state boundaries. Failure or invalid evidence on either subprocess must never mark benchmark success; prior tests enforce stale-artifact rejection and mid-run timeout failure.

The preexisting owned-only Rewrite transaction and Recovery safeguards were reviewed: journaling protects known crash windows and preserves unresolved failures, but the AdGuard API still has no atomic compare-and-swap between read and delete/add. An external writer can race the API even after a just-in-time read. Tests cannot establish atomicity; **DNS write mode remains not approved**. Actual GitHub/Twitch CDN object suitability, byte-on-wire accounting, WARP/PBR public-egress provenance, and OpenWrt read-only device preflight remain NOT ACCEPTED.

## Explicit write-entrypoint kill switch (2026-10-12)

The supported `transaction_cli.execute` entrypoint now unconditionally refuses `apply` and `recover` with an atomic-CAS blocker, independently of `dry_run` settings. Preview and recovery-preview remain read-only. This restriction applies to the **supported CLI entrypoint**, not to direct imports/calls of lower-level `rewrite_tx.reconcile(..., dry_run=False)` or `rewrite_recover.recover(..., dry_run=False)` by another privileged Python caller. Do not package, expose or invoke those lower-level write APIs in production. A stronger architecture would remove write capability from deployed artifacts entirely. No live AdGuard API write occurred.

## Cross-target evidence corruption matrix

Added a two-target runner test: target 1 returns structurally valid v3 evidence; target 2 receives separately mutated ETag, Cache classification, Content-Range, elapsed time, CV summary, byte count, missing sample, or wrong-domain replay evidence. Every mutation must fail without changing preexisting health/benchmark timestamps. These injected-second-target tests use a fake executor; the earlier two-target OS-subprocess success-path test remains real child processes. Real second-child TLS fault injection (certificate failure, truncation, timeout) is still outstanding and must not be described as complete. CDN object and WARP/PBR exits remain unverified, so auto-benchmark stays fail-closed.

## Read-only module boundary and two-target TLS fault (2026-10-12)

`readonly_bundle_manifest.py` enumerates the permitted read-only Python runtime modules, excluding `rewrite_tx.py`, `rewrite_recover.py`, `transaction_cli.py`, `tx_safety.py` and `adguard_api.py`. Its validator rejects symlinks, absent modules, and direct imports of DNS writer modules. **This is a validated allowlist, not yet a production packaging/install command**; copying the entire `openwrt/` tree would still include write-capable lower-level APIs and is NOT APPROVED. The supported CLI also refuses `apply`/`recover` unconditionally.

Auto-benchmark is rejected before loading AdGuard credentials, client modules, or untrusted route JSON. No forged evidence can turn it on. The new real two-child TLS test confirms target 1 can complete six sessions and a truncated HTTP body on target 2 causes an error without advancing benchmark or health timestamps. An eight-case per-target fake-executor v3 tamper matrix continues to cover Cache, ETag, Range, CV, elapsed time, bytes and replay. Separate real second-child certificate failure and timeout tests remain open. Real GitHub/Twitch large object and PBR/WARP public-egress trust are NOT ACCEPTED.

## Reproducible read-only package and real dual-child TLS failures — 2026-10-12

`build_readonly_bundle.py --source openwrt --output <new-empty-path>` constructs a source-only deterministic file set from `readonly_bundle_manifest.py`, writes SHA-256 hashes to `manifest.json`, and verifies actual filenames and parsed Python import dependencies. Forbidden AdGuard writer modules, direct writer imports, extra files, altered content and symbolic-link package members are rejected. Minimal CI now creates and verifies this exact bundle in a local temporary CI path; **this is not installation** and confers no production approval. Source-only package does not include settings with credentials, cron installer or Router service mutation scripts. It is not a hermetic Python sandbox; a privileged actor could still import external modules installed on a device. Enforce minimal filesystem/module privileges on any eventual deployment.

In addition to the 12-request dual-target OS subprocess success path, isolated real TLS tests now run six valid first-target requests before the second child encounters (a) a SAN hostname/certificate mismatch or (b) a stalled TLS HTTP response causing configured read timeout. Both reject the benchmark and leave existing Health/Benchmark timestamps unchanged, despite a stale second-target output artifact. A separate second-child HTTP body truncation test and fake-executor metadata tampering matrix continue to pass.

The read-only package is not approved for Router deployment, public CDN throughput benchmarking, DNS rewrite operations, cron installation, or PBR/WARP configuration. The CLI write-mode kill switch remains in place and AdGuard's lack of atomic CAS still blocks any proposed write.
