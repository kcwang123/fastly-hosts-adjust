# CDN Optimizer 0.1.0-2 — Versioned Upgrade / Rollback Operator Runbook

**Status:** GitHub-only planning. **NOT authorization to operate KCHomeMainAP.** PR #2 remains Draft. Stage E / merge excluded.

## Preconditions before any separately authorized device action
1. Confirm environment identity (KCHomeMainAP, OpenWrt 23.05.3, mediatek/filogic, aarch64_cortex-a53), existing packages and disabled UCI flags; confirm management and out-of-band recovery.
2. Record exact desired HEAD, new Core/LuCI IPK source, SHA256, architecture, dependencies and generated `postinst`/`prerm` contents. Core `0.1.0-2` declares `/etc/config/cdn_optimizer` as a conffile. Original rollback Core `0.1.0-1` **does not**.
3. Export a *private operator-side copy* of the CDN UCI configuration and its SHA256; check its completeness/permissions. Existing earlier C1 backup is sensitive and configuration-only, not a firmware rollback.
4. Have both versioned IPK pairs available **off-router** and checked against pinned manifests; files in Router `/tmp` will vanish on reboot.
5. Confirm authorized maintenance window and separately approve **B Upload**, **C Install**, **rpcd Restart (if required)**, and **Rollback Restore**. No phase inherits consent. No DNS, hosts, PBR, WARP, firewall, routing or public probes.

## Proposed stage sequence (no automatic execution)
- B: Stage the two `0.1.0-2` IPKs under a fresh, private and version-specific directory. Check both hashes on-device without overwriting existing rollback artifacts.
- C: Apply only the approved explicit package transaction. Verify installed metadata including `Depends: libc, ca-bundle, jsonfilter`, UCI values and package files. Investigate generated `default_prerm` behavior: `IPKG_NO_SCRIPT=1` is **not** proof that prerm was skipped. Do not imply that management-plane reload is authorized.
- Runtime: After separate approval for any restart, verify rpcd readiness with bounded **read-only** checks, only the `status` method, unknown `scan` rejected, flags 0, and LuCI three-page smoke.
- If a partial transaction is detected (Core upgraded but LuCI old or vice versa), **STOP**. Record exact installed versions, metadata, hashes, config and service availability. Do not blindly force upgrade, restart or rollback.
- Rollback: Only after separately approving rollback and **configuration restoration**, verify the off-router snapshot hash before downgrade. Native `opkg --force-downgrade` to original 0.1.0-1 can overwrite the customized CDN UCI config. Compare the active file to the approved pre-downgrade snapshot after downgrade and restore that snapshot only with explicit authorization; hash-verify afterward. If snapshot missing or changed, **abort before downgrade**, with no fallback guess.
- Do not auto-merge PR or enter Stage E when runtime checks pass.

## Offline evidence and limitations
- Real SDK `opkg` runs only in disposable Docker with `--network none`, read-only host mounts, bounded tmpfs, dropped caps and resource limits.
- The normal transaction proves config-preserving **upgrade** after adding conffile manifest, but native downgrade to old 0.1.0-1 lost config; explicit simulated operator snapshot restore was required.
- Fault-injection modes each use a fresh container: `partial_upgrade` (simulates interruption between Core and LuCI installation and asserts mismatch), `missing_snapshot` (abort before downgrade), `tampered_snapshot` (hash mismatch abort before downgrade). These **do not** simulate SIGKILL, power loss, full storage, corrupted opkg DB or Router service behavior.
- Generated package hooks are inspected and archived by SDK CI. Actual Router side effects of `default_postinst`/`default_prerm` remain unknown.
- Historical installed opkg dependency metadata drift root cause **UNKNOWN**; actual non-admin ACL session remains **BLOCKED** (all existing accounts admin).
