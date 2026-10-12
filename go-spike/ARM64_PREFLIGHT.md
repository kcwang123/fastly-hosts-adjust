# ARM64 Read-only Preflight — Phase A only

**Status: RELEASE NO-GO. No router access is authorized.**

## Scope and provenance

CI builds from the **exact triggering commit**, using Go version from
`go-spike/go.mod`, `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOARM64=v8.0`,
`-trimpath -ldflags="-s -w"`. Two binaries are retained as a short-lived
GitHub Actions artifact alongside `SHA256SUMS` and `BUILD-IDENTITY.txt`.
The checksum is an integrity cross-check, **not** a cryptographic
attestation of trusted build infrastructure or reproducibility. Do not
assume byte-for-byte reproducibility until separately established.

- `fastly-readonly-arm64` — basic offline config validation CLI; it has
  no public network or DNS entrypoint.
- `fastly-local-health-arm64` — localhost TLS **test harness**, requiring
  a test CA and loopback listener; **not** the production scanner and
  **not authorized for on-router execution**.

Confirm the GitHub Actions run is for the current branch SHA, successful,
and the artifact's `BUILD-IDENTITY.txt` contains that same SHA.
Artifact expires after 7 days. Store the SHA and checksums with review
records before any later deployment decision.

## Explicit phase gates

| Phase | Permitted without further approval? | Description |
|---|---|---|
| A | Yes | GitHub CI build, checksums, offline tests, documentation |
| B | **No** | Copy any file/binary to Router |
| C | **No** | Execute any ARM64 binary on Router, including `--help` |
| D | **No** | Connect to public candidate IPs, benchmark or CDN |

Each of B/C/D requires **separate operator authorization**. Authorizing
one does not authorize any other phase. No installation, package upgrade,
Cron, DNS/DHCP/PBR/WARP changes or automatic benchmarks.

## Preflight checklist (documentation only)

1. Verify exact commit and build identity; download the artifact to a
   separate trusted workstation and run `sha256sum -c SHA256SUMS`
   **on that workstation**. Never treat a checksum delivered within the
   same artifact as independent supply-chain verification.
2. Confirm ARM64 ELF, static linking and Cortex-A53 instruction support.
   Cross-compilation alone does not prove the binary executes on the router.
3. Before B, document Router free memory, overlay storage, current
   processes, router-appropriate path, intended root-owned 0700 directory,
   0600 state/test inputs and 0700 executable. The router's existing
   System CA trust must be separately validated; do not copy CI test CAs.
4. Before C, require an explicit **non-public** dry-run-only command
   manifest, evidence retention path and per-command rollback/cleanup plan.
   Current localhost harness is not a candidate for C.
5. Before D, independently validate PBR/WARP real public egress and
   domain/IP allowlist, failure budgets, HTTP Range/ETag/cache identity.
   This phase is not part of current preflight acceptance.
6. Cleanup for any future B/C must be separately approved and limited
   to the precise files created by that phase; no removal of shared
   system CA, network settings or service configuration.

## Known limitations / release blockers

Go special-use IPv4 filtering intentionally favors false-negative
rejection and is not a strict reproduction of Python `is_global`.
The local harness locks cooperating processes only; file permission
checks and parent-directory defenses cannot eliminate all TOCTOU.
A non-cooperative injected Probe cannot be force-killed by Go Context
timeouts. Local test CA is not System CA trust evidence. CI AMD64 RSS
(including localhost TLS test server) is not OpenWrt ARM64 RSS.

`dry_run=true`, `auto_benchmark=false`. DNS Rewrite remains
**BLOCKED** due to missing atomic compare-and-swap and target-specific
external evidence. Original Python Draft PR #1 remains unchanged.
**Release decision NO-GO**.
