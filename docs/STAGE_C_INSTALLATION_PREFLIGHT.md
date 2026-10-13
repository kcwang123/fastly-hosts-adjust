# Stage C — Offline installation preflight and independent authorization

Status: **OFFLINE REVIEW ONLY. Stage C is NOT AUTHORIZED.**
Environment: Home / `KCHomeMainAP` at `192.168.1.240:22` (operator-managed Windows OpenSSH).
PR #2 baseline before this document: `b1e71fcf3454d3e93de1eae7c6207cd0dee5aeb3`.
Package source pinned: `522591c0edae4cfb68dcf9b7166c7280d34034c2`.
Artifact ID `11791141767`; Stage B has user-supplied **remote SHA256 OK** for both IPKs in `/tmp/cdn-optimizer-stage-522591c0`.
No Router command, installation, new binary execution, restart, active probe, DNS/firewall/routing/PBR/WARP change, cleanup or merge is authorized by this document.

## Verified / inferred / unknown

| Category | Evidence | Result |
|---|---|---|
| Source/package identity | Stage B operator log, SHA256SUMS, artifact identity | Verified by submitted output; no independent Router read-back |
| Core package | `cdn-optimizer 0.1.0-1`, aarch64_cortex-a53, Depends libc/ca-bundle | Offline verified |
| LuCI package | `luci-app-cdn-optimizer 0.1.0-1`, all, Depends libc/cdn-optimizer/luci-base | Offline verified |
| Device packages | ca-bundle/rpcd/luci-base/rpcd-mod-file/rpcd-mod-luci were observed | Partial; `opkg` prospective dependency resolution untested |
| Init | `/etc/init.d/cdn-optimizer` defines a passive `start_service(){ return 0; }` | Static verified, install hook side effects unknown |
| UCI | `enabled=0`, `allow_public_probe=0` in packaged default | Static verified; installation effects on existing config unknown |
| rpcd | Only `status` exported; ACL restricts ubus `cdn-optimizer.status` and UCI read | Static verified; runtime/plugin registration/auth tests pending |
| Maintainer hooks | Generated `postinst`/`prerm` delegate to OpenWrt default_postinst/default_prerm | Verified present; effective behavior on device unknown |
| Management | Valid SSH key/read-only user test and physical possession | Verified login; recovery after management-plane loss not tested |

## Blocking finding: Router BusyBox lacks `stat`

Stage B v1 failed `ash: stat: not found`; package source `openwrt/cdn-optimizer/files/usr/libexec/cdn-optimizer/run-once` contains `stat -c %u "$STATE"`. This will fail when authorized one-shot execution reaches that line unless the runtime dependency is added or the code changed. **Do not install the currently staged IPKs as a completed/production-ready integration.**

Required GitHub-only engineering before Stage C approval: replace or explicitly provide the missing runtime dependency; add a focused test using an environment without `stat`; rebuild exact-head SDK packages and repeat manifest + Stage B integrity check for any changed package. This does not authorize installing any dependency or binary on the router.

## Risks / installation behavior

- `postinst` and `prerm` default helper calls may trigger service actions, init enable/disable and LuCI/rpcd cache behavior; review actual SDK helper and (in separately authorized read-only device inspection) target helper before any Stage C apply.
- Core places files under `/etc/config`, `/etc/init.d`, `/usr/bin`, `/usr/libexec/rpcd`, `/usr/libexec/cdn-optimizer`, `/usr/share/rpcd/acl.d`; LuCI under `/www/luci-static/resources/view/cdn-optimizer` and `/usr/share/luci/menu.d`. Existing file collisions/config overrides are No-Go.
- `/tmp` staging is volatile; reboot loses staged files; never reboot as a cleanup or recovery shortcut without separate consent.
- rpcd ACL session tests must cover allowed status, denied unexpected calls and write actions, stale `/tmp` result/symlink. No active CDN public probe in Stage C.
- Router has br-lan and eth1 both in 192.168.1.0/24; ensure a second working local management path before maintenance. CF_Warp unconfigured, remains out of scope.

## Dependency closure

Only package control Depends is known: core `libc, ca-bundle`; LuCI `libc, cdn-optimizer, luci-base`. Verified installed previously: ca-bundle, rpcd, luci-base, rpcd-mod-file, rpcd-mod-luci. Offline package metadata does not ensure transaction resolver closure or absence of replacement/removal. Any future install plan must first obtain dry-run evidence if opkg's exact version supports it, without feed refresh or network access; otherwise mark UNKNOWN, not infer success.

## Backups, rollback and maintenance

Before Stage C: specify a maintenance window, wired local fallback, Router config/archive backup location and verified restore method. Backup creation is a separate Router-write authorization, not an automatic side effect of this preflight. Preserve baseline package list, relevant `/etc/config` and rpcd/LuCI state **with secrets redacted outside the local backup**. Rollback must account for postinst/prerm effects, cached LuCI menus, rpcd ACL registration and uploaded stage files; do not assume `opkg remove` is side-effect-free. Stop on SSH instability, unexpected installs, unexpected service restarts or a changed route/DNS/firewall baseline.

## Stage C prospective operator sequence (NOT APPROVED)

1. Confirm updated source/artifact SHA, individual IPK digests and re-staging evidence; stop if staged hashes no longer match.
2. Review all `postinst/prerm` scripts and device helper effects, installed packages, config collisions and current management route.
3. Confirm backup and rollback availability, maintenance timing, recovery and allowed monitoring scope.
4. Request **independent C1 backup**, **C2 installation/hooks**, and **C3 local read-only runtime smoke** approval as distinct actions. C3 must not invoke `run-once` or any active network probe.
5. Perform only explicitly approved stages, record before/after package state and errors; pause before D public probe. Network config changes remain E-only.

## Windows / Codex worker prompt — OFFLINE ONLY

Continue `kcwang123/fastly-hosts-adjust` PR #2 from live exact branch head; read `docs/STAGE_C_INSTALLATION_PREFLIGHT.md`, `docs/STAGE_B_UPLOAD_AUTHORIZATION.md` and Makefiles/packaged scripts. Stage B remote checksum was operator-confirmed. **Current authorization is offline review ONLY**. Audit package hooks, dependency closure, rpcd/ACL/LuCI, UCI defaults, BusyBox ash compatibility, backup and rollback. Treat confirmed `stat` absence as a blocker; propose focused GitHub feature-branch fix with a no-stat fixture and exact-head CI. Do NOT SSH/SCP to Router, install, run binaries, restart services, probe public networks, clean up staged files, write configs, alter DNS/PBR/WARP/firewall/routing or merge. Preserve PR #1 independent and PR #2 Draft. Deliver blocker matrix, evidence, exact SHA, and separately scoped C1/C2/C3 approval request.
