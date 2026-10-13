# CDN Optimizer MVP — C3/D acceptance and release gates

## Evidence, 2026-10-14 (operator-supplied)
- C1: Router configuration backup created and verified (sensitive archive stays local).
- C2: core and LuCI IPKs installed on KCHomeMainAP, OpenWrt 23.05.3.
- C3: one authorized rpcd restart registered `cdn-optimizer.status`; status responded `not_tested`, `safe_to_apply=false`.
- C3: static ACL/menu script passed. Browser screenshots show Overview, Results and Settings rendered.
- D: exactly one authorized read-only `github` probe against `raw.githubusercontent.com` using DNS-derived `185.199.110.133`: TLS verified, HTTP 206, 4096 bytes, 267 ms CLI duration, cache HIT. A single successful observation is **not** an optimized candidate recommendation.
- No DNS/hosts/PBR/WARP/firewall/route change, UCI write, reboot or Stage E application.

## Current limitations / unverified
1. Authenticated *non-administrator* LuCI/ubus session permission negative test has not run. Static ACL JSON tests are not equivalent.
2. Browser JavaScript console/network error check is not recorded. Screenshots alone establish basic render only.
3. New commits after installed IPK head are **offline only**, not Router-verified. Rebuild and separately approve upgrade before reporting deployment parity.
4. A cached successful HTTP 206 does not measure user traffic or establish p50/p95 reliability.

## Real session ACL negative test (operator, read-only)
Do not create a new router account, expose session IDs, or broaden ACL for testing. Reuse an existing non-admin account **only if one is already available** with the `luci-app-cdn-optimizer` read grant and no write permissions. If none exists, mark blocked — do not weaken security to satisfy the test.

1. Log into LuCI with that account in a private browser session. Confirm Overview/Results/Settings are viewable where allowed.
2. Open browser Developer Tools Network; view the authenticated ubus requests without pasting session tokens into reports.
3. Using that account's existing RPC capability, confirm `cdn-optimizer.status` is allowed and `cdn-optimizer.scan`, `uci.set` on `cdn_optimizer`, and non-allowlisted RPC methods are rejected as *permission denied or method not found*; **never submit a mutating UCI call** purely to test authorization. Instead use a non-mutating session `access` check for write privileges, if exposed and supported.
4. Capture only method names, booleans/status codes and screenshots with secrets redacted. Do not share cookies, passwords, tokens or configuration backups.
5. If browser/session behavior differs, stop and inspect; do not automatically reload rpcd or uhttpd.

## Security review gates
- [x] rpcd plugin lists only `status`; CLI probe requires opt-in flag.
- [x] LuCI ACL contains read grants only; no write/file/exec grants.
- [x] UCI enabled and allow_public_probe default to 0.
- [x] Router Stage D once passed with TLS validation and bounded HTTP response.
- [x] LuCI 3 pages basic render.
- [ ] Non-admin *actual session* ACL acceptance / documented blocked status.
- [ ] Browser console / network errors verified.
- [ ] Final exact-head focused tests and all required CI green.
- [ ] Exact-head IPKs checksums/manifest reissued after code changes and device version checked (if seeking deployment acceptance).
- [x] Offline implementation: rpcd result requires root-owned 0700 directory, root-owned 0600 file, bounded bytes, and jsonfilter schema_version=1 / safe_to_apply=false / mode=read_only. Package explicitly depends on jsonfilter; offline guards added.\n- [ ] Security regression runtime verification: hostile fixtures (malformed JSON, wrong owner/mode, symlink, oversized, missing jsonfilter) and exact-head CI; no claim of device verification.\n- [ ] Remaining race/contract analysis: validation and cat are separate file reads; JSON field checks are not a full strict schema/duplicate-key validator.
- [ ] Separate explicit authorization for any Stage E network apply.
- [ ] Merge conditions and owner approval verified; PR remains Draft.

## UX
- Overview is parent route (`/admin/services/cdn-optimizer`), Results and Settings are child tabs. Two visible tabs with working parent page is expected current menu behavior.
- Settings must display **unavailable**, not **disabled**, if UCI cannot be read (offline fix pending fresh build/deployment).
- Keep read-only presentation and `safe_to_apply=false`; avoid adding controls that suggest probe/apply capability.

## Rollback / scope
Only GitHub code and documentation were modified in this iteration. No router operations. Do not reuse a backup as a full firmware restore. Do not upgrade installed packages or reset services without explicit scope approval.
