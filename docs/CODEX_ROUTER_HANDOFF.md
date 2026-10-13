# Codex SSH Router Handoff — separate authorization gates

Status: **GitHub-side preparation only**. This document is not approval to access a Router. Target is the user's OpenWrt 23.05.3 / mediatek/filogic device **only after live read-only identification confirms it**. Preserve PR #1, DNS ownership, AdGuard, PBR and WARP.

## A — Offline only (currently authorized)

- Review exact PR #2 Head, latest four CI outcomes and pinned SDK provenance.
- Verify IPK control/data manifests, `Architecture: aarch64_cortex-a53`, dependency closure, executable permissions, static ELF and SHA256.
- Confirm actual release artifact is from that exact Head, not a PR merge-ref SHA.
- Do not infer that CI Green proves LuCI/rpcd functioning on Router.
- A working HTTPS probe is an active network request, **not** an inert read-only preflight.

## B0 — Read-only Router inspection (requires explicit Router-access approval)

Using an authorized Codex SSH environment and bounded commands only: record device model, `ubus call system board`, `uname -m`, `opkg print-architecture`, firmware/kernel, BusyBox version, CA bundle existence, `df`, `free`, rpcd and LuCI installed packages, UCI availability, port ownership and current procd/rpcd status. Never print credentials or secrets. Do not upload or execute new binaries. Use a redacted evidence report.

**Go/no-go:** correct device, verified architecture/package ABI, resource budget, management access/rollback, unchanged live DNS/routing state.

## B — Upload (separate explicit approval)

Only after B0, transfer the **exact** vetted artifacts to a designated temporary staging directory; re-check SHA256, owner, permissions, storage. Upload does **not** permit install or execute.

## C — Execution / installation (separate explicit approval)

Explicitly agree on maintenance window, recovery access and rollback before installing packages or invoking new binaries. Check `rpcd` object `cdn-optimizer`, method list/status, allow and deny ACLs for test sessions, LuCI three-page rendering. Validate lock, private `/tmp` state, atomic storage, failure handling, CA validation and runtime RSS without activating a public probe.

## D — Public probing (separate explicit approval)

Only with an explicitly approved service, public candidate IP, request/time/byte budget and route context. Never assume a manually entered IP belongs to the intended CDN; DNS/PBR/WARP egress still requires independent evidence. No unattended timers or bulk scan.

## E — Config Writer (out of scope, separate future authorization)

Any DNS/AdGuard Rewrite/hosts/firewall/routing/PBR/WARP changes require a distinct reviewed change, backups and rollback. Neither `safe_to_apply: false` nor `recommend_review` authorizes apply.

## Rollback and stop

If architecture, permissions, TLS/CA, lock, RPC ACL, service health or WAN continuity disagree with expectations, stop at the current gate. Before any install, define exact package uninstall/restore steps and OOB recovery. Never forcibly remove a lock while a process might be running.

No Router SSH, uploads, execution, public probes or config mutation were performed when writing this handoff.
