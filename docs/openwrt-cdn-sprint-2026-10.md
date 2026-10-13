# OpenWrt CDN Diagnostics — three-day sprint

**Window:** 2026-10-13 through 2026-10-16 (Asia/Taipei). **Status:** Sprint branch created; implementation and router validation pending.

## Verified baseline

- Starting branch: `spike/go-arm64-readonly`, historical exact-green commit `cc6585755ef0af1c3125e36e387a0b7f703051fb` (not independently verified as present head).
- Existing `go-spike` consists of an offline config-only CLI, fixture scheduler, and localhost-only TLS harness. These **do not** perform real public scanning.
- Existing Python Draft PR #1 remains independent.
- Router from user read-only output: OpenWrt 23.05.3; WARP down; PBR disabled; no authorized installation or real public probing.
- GitHub Issues are disabled (attempt returned HTTP 410); sprint tracked on branch instead.

## MVP (in scope)

1. Go 1.22 linux/arm64 build with SHA256, version+commit provenance and reproducible build steps.
2. Strictly bounded **read-only** public HTTPS diagnostic scanner with explicit allowlisted FQDN and probe paths, TLS hostname verification, deadlines, request/byte budgets and stable JSON output. Must not claim to optimize routes without verified evidence.
3. OpenWrt 23.05 `procd` managed one-shot job, `UCI` configuration, read-only status/result storage, fail-closed permissions and no concurrent scans.
4. `rpcd` capability-restricted status/result/scan actions and minimal `luci-app-cdn-optimizer` Overview/Results/Settings.
5. Notification integration *only if* core quality gates are met; Telegram CTA limited to details/retest.
6. Installation, removal and rollback runbook, focused tests, exact-head CI evidence and acceptance record.

## Day 1 — Core and offline verification

- Reconcile current exact branch SHA, PR, CI and repository instructions.
- Inspect existing scanner/probe/scheduler and reuse only verified contracts.
- Introduce minimal public-health command, structured output with `mode: read_only`, explicit `network_executed`, and stable error/status distinctions.
- Run targeted Go tests including TLS hostname, invalid inputs, timeout, byte ceiling, concurrency, allowlist and fail-closed behavior.
- Build ARM64 artifact and checksum on CI; no router activity.

## Day 2 — OpenWrt packaging and LuCI

- Package architecture validation and `procd` one-shot service; safe default config.
- Constrained `rpcd` interface; no arbitrary command execution or web-exposed write endpoint.
- Minimal JS LuCI pages calling exact RPC contract.
- Offline package/static tests; UI/ACL validation.

## Day 3 — Release quality gates

- Add notification adapter only if safe and bounded; avoid a second scheduler.
- Review risk and verify exact-head CI, provenance, artifacts.
- Document manual / rollback runbook and open permission gates.
- Do not claim router-ready until OpenWrt musl/CA/memory and public egress are explicitly tested.

## Hard boundaries

- **A GitHub code/package/offline validation:** permitted.
- **B Upload artifact to router:** needs distinct explicit user approval.
- **C Execute on router:** needs distinct explicit user approval.
- **D Real public probes from router:** needs distinct explicit user approval.
- **E Modify DNS/AdGuard/hosts/PBR/WARP/UCI network:** out of scope; separately authorized future Writer.
- No Cron, unattended active scans, forced Cloudflare IP, unvalidated CDN service-IP swapping, or outbound secrets by default.
- `Read-only` describes router configuration mutations; benchmark requests still use bandwidth, so cap them explicitly.

## Definition of done

- Versioned results schema consumed by CLI, rpcd, LuCI and alerts without incompatible transformations.
- CLI and ACL fail closed; tests for negative/security paths green.
- Install/remove does not modify active DNS/routing and leaves working WAN unchanged.
- UI shows actual measurements plus timestamps and failure states, never fabricated current performance.
- Release artifact reproducible + SHA256 and source commit identity.
- Remaining authorization/evidence blocks disclosed before release.

## Risk / schedule cut rule

If Day 2 discovers incompatibility, **cut optional providers and Telegram first**. Prefer a verified Fastly read-only scanner, minimal LuCI status UI and safe package over multi-CDN scope or DNS Writer. No relaxation of CI or router authorization gates to meet the date.
