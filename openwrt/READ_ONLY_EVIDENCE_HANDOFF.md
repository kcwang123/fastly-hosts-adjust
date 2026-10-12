# Operator Read-only Evidence Handoff — NOT ACCEPTED

PR: [#1](https://github.com/kcwang123/fastly-hosts-adjust/pull/1) (Draft; do not merge)  
Basis: `RELEASE_DECISION_MEMO.md` and `READ_ONLY_PREFLIGHT_CHECKLIST.md`  
Initial decision: **NO-GO**. This form collects evidence only; it does not authorize deployment.

## Session record (operator completes)

| Field | Entry |
| --- | --- |
| Observation date/time and timezone | TBD |
| Operator and approving owner (role/alias; avoid personal secrets) | TBD |
| Device ID / OpenWrt release / architecture (redacted) | TBD |
| Python version / execution identity | TBD |
| GitHub commit SHA / evidence package revision | TBD |
| Exact read-only command or independent observation source | TBD |
| Redacted output attachment/link and checksum, if retained | TBD |
| Evidence freshness, provenance, caveats | TBD |

Before copying any output, remove credentials, tokens, private keys, secret URLs,
internal identifiers and unnecessary private addresses. Preserve enough context
to assess the observation. Do not run anything without operator authorization.
Never include `uci set`, service restart, Cron write, DNS rewrite, PBR/WARP
configuration, or a live public-CDN benchmark in this read-only session.
Any future CDN object/egress acceptance evidence requires a **separately
approved**, bounded verification plan; do not treat this form as authorization.

## Gate observations — fill one row per gate

Observation status and release acceptance are separate fields: CI tests can be
PASS while the corresponding real-device evidence stays UNKNOWN and release
acceptance remains NOT ACCEPTED.

Use **PASS** only for complete, independently reviewable observations that
meet the applicable rule in `READ_ONLY_PREFLIGHT_CHECKLIST.md`. Use **FAIL**
only if supplied evidence disproves the rule. Use **UNKNOWN** for missing,
outdated, ambiguous or redacted-beyond-use evidence. **NOT ACCEPTED** is a
release decision, not a claim that a test physically failed.

| Gate | Status (PASS / FAIL / UNKNOWN) | Observation timestamp + exact command/source | Redacted evidence link or excerpt | Reviewer / NO-GO reason |
| --- | --- | --- | --- | --- |
| OpenWrt OS / Python / required stdlib | UNKNOWN | TBD | TBD | No device evidence |
| Overlay storage >= 10 MiB | UNKNOWN | TBD | TBD | No device evidence |
| AdGuard :53, dnsmasq :54, DHCP :67 and binding ownership | UNKNOWN | TBD | TBD | Listener/process ownership unverified |
| Separate deployer vs low-privilege Runtime identity | UNKNOWN | TBD | TBD | No live account/ACL evidence |
| Bundle SHA-256, imports, manifest, parent/ancestor owners, ACL, mount | UNKNOWN | TBD | TBD | CI-only package validation is insufficient |
| System Python / site-packages and `-I` runtime environment | UNKNOWN | TBD | TBD | System import roots unverified |
| OS CA roots provenance, ownership and TLS hostname validation | UNKNOWN | TBD | TBD | System trust source not attested |
| GitHub/Twitch stable large objects: both IPs, 206, Range, ETag, Cache | UNKNOWN | TBD | TBD | Real CDN targets NOT ACCEPTED |
| Per-target PBR/WARP public egress corroboration | UNKNOWN | TBD | TBD | Local routes alone insufficient |
| AdGuard atomic CAS and conflict-safe transaction/recovery | UNKNOWN | TBD | TBD | Write feature permanently BLOCKED absent redesign |

If separately authorized public CDN or PBR/WARP evidence is later available,
record the hostname and exact object identity or destination pair, observation
time, method and independent egress attestation. Otherwise leave UNKNOWN.
Do not interpret a loopback TLS test, cached local scan or `ip route` output
as proof of a public CDN object or public exit.

## Reviewer disposition (must complete; default NO-GO)

- Evidence review date/time + reviewer: **TBD**
- Any missing, failed or disputed gate: **YES — all device-dependent rows UNKNOWN**
- Current GitHub/Twitch CDN source decision: **NOT ACCEPTED**
- Current PBR/WARP public exit decision: **NOT ACCEPTED**
- Current system CA and device permission decision: **NOT ACCEPTED**
- DNS Rewrite: **BLOCKED** (AdGuard Delete/Add has no proven atomic CAS)
- Automatic benchmarking, Router deployment and Cron: **BLOCKED**
- **Release decision: NO-GO**
- Specific next evidence required: operator-approved, non-invasive device
  observations from `READ_ONLY_PREFLIGHT_CHECKLIST.md`; independently verified
  CA, ownership, public target objects and target-specific egress, with a
  separate release approval if requirements ever change.

## Handling and boundaries

All observations must be collected by the operator or specifically authorized
agent in a **read-only** session; this file is an unfilled handoff, not executed
evidence. CI success establishes only tested code behavior. Neither the
self-verified manifest nor the isolated Python launcher is an OS sandbox;
system modules, CA sources, parent-path replacement and TOCTOU remain distinct
trust questions. No Router connection, deployment, Cron enablement, network
benchmark or DNS/DHCP/PBR/WARP change is authorized by this form.

Keep `dry_run=true` and `auto_benchmark=false`. Leave PR #1 Draft and
unmerged. A reviewer cannot override the DNS write prohibition by marking
unrelated gates PASS.
