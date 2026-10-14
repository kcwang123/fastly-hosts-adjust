# Stage B upload authorization packet — NOT APPROVED

Exact source HEAD: `522591c0edae4cfb68dcf9b7166c7280d34034c2`
GitHub SDK run `38351014679`; artifact `11791141767`.
B0 device: `KCHomeMainAP` (CMCC RAX3000M / OpenWrt 23.05.3 / mediatek/filogic / `aarch64_cortex-a53`).
**This document is preparation. No SSH, SCP, directory creation, Router cleanup or other Router operation is authorized.**

## Exact offline IPK manifest

| File | SHA256 | Architecture | Declared depends |
|---|---|---|---|
| `cdn-optimizer_0.1.0-1_aarch64_cortex-a53.ipk` | `ea6a457ac8ec5ca548a4ca848480812b3169ca5473436213201253a7a7155d24` | `aarch64_cortex-a53` | `libc, ca-bundle` |
| `luci-app-cdn-optimizer_0.1.0-1_all.ipk` | `e43f17b70e54766214d244d1492ce3eda0db7908b50ccaaa51a56b9d8ad96c73` | `all` | `libc, cdn-optimizer, luci-base` |

From actual locally unpacked GitHub artifact, not only the CI result. `BUILD-IDENTITY.txt` matched the exact source SHA. Core includes binary, one-shot, rpcd plugin, ACL, config and init; LuCI contains three JS views and menu. Both contain generated `postinst` / `prerm` calling OpenWrt `default_postinst` / `default_prerm`. Those scripts **must not run at Stage B**. No dependency resolver or router hook runtime was tested.

## Exact Stage B authorization request (do not assume approval)

The operator must explicitly approve all of:

1. **Environment/target:** Home router `KCHomeMainAP` with separately supplied reachable management address; verify device identity again before writes. Never guess address from earlier `192.168.1.240` / `192.168.1.101` (same subnet on LAN/WAN).
2. **Transfer boundary:** authorize Codex to open SSH/SCP **only to that host**, stage **only** the two IPKs and a `SHA256SUMS` file, no other content.
3. **Temporary storage:** `/tmp/cdn-optimizer-stage-522591c0`, owned by root, `0700`; file mode `0600`. Directory creation is mutating and needs Stage B permission. No symlink, existing files, `/overlay`, `/etc` or live service paths.
4. **Verification:** read-only identity/resource checks, remote `sha256sum -c`, `ls -l`, `opkg print-architecture` and package-name/control metadata. No `opkg install`, `opkg update`, `opkg configure`, `chmod +x`, init/service restart or executing staged content.
5. **Cleanup:** deletion of *only* the newly created exact stage directory/files is a separate mutating action, not automatically implied by transfer. No `rm -rf` against an unverified path.
6. **Stop conditions:** wrong host/identity, unsupported opkg arch, altered HEAD or IPK digest, collision/symlink, unexpected owner/perms, low /tmp headroom, unstable management connection, or no accessible recovery route. Do not auto-retry with relaxed permissions.

Physical possession and likely root credentials are not a demonstrated LAN/failsafe recovery. CF_Warp remains disabled/unfinished, not a prerequisite. LAN and WAN share 192.168.1.0/24; do not modify either as part of this work.

## Future Stage B sequence — only after explicit authorization

The following is **design text, not permission to execute**.

**Local workstation:**
```sh
# Local offline reference commands; not Router commands
gh run download 38351014679 -R kcwang123/fastly-hosts-adjust -n openwrt-filogic-sdk-ipk-522591c0edae4cfb68dcf9b7166c7280d34034c2
sha256sum -c SHA256SUMS
cat BUILD-IDENTITY.txt
```

**Router upload workflow once approved:** verify identity and `df -h /tmp`; check path absent and no symlinks; `umask 077`, create root-only staging; SCP exactly 3 listed files; check root ownership and `0600` permissions; run `sha256sum -c SHA256SUMS` in the stage directory. On any mismatch stop, report, do not install or clean up automatically.

SSH/SCP transport details depend on Codex's local OS/SSH agent, router authentication and approved address. Do not include passwords, private keys or tokens in prompts or GitHub logs.

## Stage C Go/No-Go

Even if B completes, request **separate C authorization** before any install, execution, restart, rpcd registration, LuCI browser runtime test or device cleanup. Check package dependency closure using installed package data, inspect target `/lib/functions.sh` default hooks **read-only** under approved access, arrange maintenance window, configuration backup through approved process, recovery path and precise package rollback. Do not conflate SDK Package Verified with Router Runtime Verified.

## Codex SSH/SCP Worker Prompt — queued, not executable

> Continue `kcwang123/fastly-hosts-adjust` PR #2 at exact source `522591c0edae4cfb68dcf9b7166c7280d34034c2`. Read `docs/STAGE_B_UPLOAD_AUTHORIZATION.md` and its manifest. Confirm PR #1 independent, PR #2 Draft, four matching green CI runs, SDK artifact 11791141767 and both individual IPK hashes. **Current authorization is OFFLINE PREPARATION ONLY. Do not connect via SSH, upload, create a remote directory, execute any binary, install, run active probes, restart services, clean remote files or modify network config.** Produce a concrete Stage B authorization request identifying Home Router SSH target, operator/credential method (never record secrets), staging path, transfer file allowlist, expected hashes, resource and management checks, stop conditions and cleanup consent. After a future explicit Stage B user approval, perform only the approved SSH/SCP staging and remote checksum verification; stop there. Never auto-advance to C/D/E. Preserve WARP off and existing DNS/AdGuard/PBR/routing, and return Verified/Inferred/Unknown evidence and Go/No-Go.

## Artifact expiration / version drift

GitHub Actions artifacts are time-limited (workflow retention currently 7 days). If the exact artifact expires, do not substitute a newer or older IPK silently: re-establish exact source identity, CI provenance and hashes with a separately reviewed artifact.
