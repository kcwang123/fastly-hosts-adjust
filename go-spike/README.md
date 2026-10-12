# Go ARM64 Read-only Runtime Spike — NOT APPROVED FOR ROUTER DEPLOYMENT

Independent branch `spike/go-arm64-readonly`, based on Python Draft PR #1 at
`68f10d26d11411a5dd98f793bd06f701afa02172`. The original PR and its
164 tests are unchanged.

## Scope and contracts

- Offline CLI `cmd/fastly-readonly`: accepts **only** a minimal JSON object
  `{"dry_run":true,"auto_benchmark":false}`. All other keys, missing fields
  and write-enabled configurations fail closed. It emits diagnostic
  `schema_version=1,status=validated_only,safe_to_apply=false,
  network_executed=false` to stdout. The basic validated-only CLI mode never writes files; the explicit offline
  Scheduler fixture mode may update only the provided state path on success.
- Offline Scheduler fixture mode: `--config <minimal-config> --state <state.json>
  --scan-input <scan.json> --now <epoch>`. Uses validated scanner schema v1
  diagnostics only; rejects malformed/unsafe evidence before atomically updating
  `last_health_epoch`. Skip and benchmark-pending outcomes never modify state.
  **No real scanner is implemented or invoked**; inputs are pre-created fixtures.
  Config is an intentionally narrow subset of Python Settings, not drop-in
  compatibility. A missing scan fixture cannot be reported as a successful scan.
- Library `internal/probe`: approved TLS hostname allowlist and paths from
  Python `tls_verify.py`; bounded HTTP 206 Range, Content-Range,
  Content-Length, ETag/X-Cache observation and transport hostname validation.
  It has NO CLI entrypoint to start a public network probe.
- Routing: deliberately NOT ported. Local `ip route get` is diagnostic only,
  never accepted as target-specific PBR/WARP public exit proof.
- JSON: **not a drop-in replacement** for Python Settings, scanner schema v1
  or benchmark evidence v2/v3. Validated-only diagnostic schema is separate;
  no result may authorize DNS writes.

## Build and evidence

```sh
cd go-spike
GOPROXY=off go test ./...
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOARM64=v8.0 GOPROXY=off \
  go build -trimpath -ldflags="-s -w" -o /tmp/fastly-readonly-arm64 ./cmd/fastly-readonly
```

GitHub CI reports the measured binary size and rejects binaries >=10 MiB.
Actual ARM64 device runtime RAM, latency, storage impact and OpenWrt system
CA integration remain **UNKNOWN** until an approved target-device test.
Host Go tests do not prove an ARM64 binary actually runs on Cortex-A53.

## Safety / decision

`dry_run=true`, `auto_benchmark=false`; no DNS transaction, hosts, UCI,
nftables, Cron, Router install, or public CDN benchmark. Static Go builds do
not prove package origin, CA provenance or routing/egress authenticity.
AdGuard has no atomic CAS: **DNS Rewrite BLOCKED**.
GitHub/Twitch large-object suitability, actual PBR/WARP public egress,
system CA provenance and runtime process identity: **NOT ACCEPTED**.
Release is **NO-GO**. Promotion from this spike requires an explicit
architectural decision and separate operator-approved evidence.
