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
- [x] Exact-head 89d8a65b: 4/4 required CI SUCCESS; hostile rpcd fixture step explicitly SUCCESS (prior to this docs-only change).
- [ ] Exact-head IPKs checksums/manifest reissued after code changes and device version checked (if seeking deployment acceptance).
- [x] Offline implementation: rpcd result requires root-owned 0700 directory, root-owned 0600 file, bounded bytes, and jsonfilter schema_version=1 / safe_to_apply=false / mode=read_only. Package explicitly depends on jsonfilter; offline guards added. 
- [x] Offline hostile-fixture harness added for malformed JSON, duplicate field, oversized payload, invalid contracts, symlink and unavailable parser (its parser is a test double; not evidence of production jsonfilter duplicate-key rejection). 
- [ ] Complete wrong owner/mode hostile fixture cases, verify exact-head CI, and run target OpenWrt jsonfilter contract before device acceptance. 
- [x] Read-once bounded shell payload snapshot: JSON checks and final output use the same captured bytes, reducing validation-to-cat TOCTOU. 
- [ ] Filesystem path metadata check to snapshot-read remains a race under adversarial writable directory conditions; root 0700 state directory mitigates unprivileged replacement, but not hostile root processes. 
- [ ] Production jsonfilter field checks do not guarantee a strict full-schema/duplicate-key validator; do not claim strict JSON validation.
- [ ] Separate explicit authorization for any Stage E network apply.
- [ ] Merge conditions and owner approval verified; PR remains Draft.

## UX
- Overview is parent route (`/admin/services/cdn-optimizer`), Results and Settings are child tabs. Two visible tabs with working parent page is expected current menu behavior.
- Settings must display **unavailable**, not **disabled**, if UCI cannot be read (offline fix pending fresh build/deployment).
- Keep read-only presentation and `safe_to_apply=false`; avoid adding controls that suggest probe/apply capability.

## Rollback / scope
Only GitHub code and documentation were modified in this iteration. No router operations. Do not reuse a backup as a full firmware restore. Do not upgrade installed packages or reset services without explicit scope approval.

## 2026-10-14 snapshot hardening follow-up
- Offline rpcd status uses one bounded shell JSON snapshot for contract checks and response, avoiding separate validation/read path payloads; path validation/open TOCTOU remains theoretically possible. No Router execution.
- Offline hostile fixtures added (malformed, invalid schema/mode/safe_to_apply, wrong file/dir mode, oversized, symlink). Their mock jsonfilter rejects duplicate keys, but OpenWrt jsonfilter behavior is **not equivalent**: strict duplicate-key rejection remains unverified and should not be claimed as closed.
- Exact-head SDK IPK must be rebuilt after changes; artifact from head eac4321c (`11832818111`, ZIP digest SHA256 de88ea0c4e32f3dc0aec086cb24f9b7b1bfbd8acc13c11af0e997420b357897e) is previous-head evidence only, not the final package. Archive digest is not the IPK checksum.

## Exact-head 89d8a65b SDK evidence
- CI run 38437888881 SUCCESS, artifact 11833134098 source commit matches head and ZIP digest SHA256 5ae269562bbf0c17608787e172ce1ffea257ad9f081a43d4b4d9e585b3169222.
- Workflow asserts architecture `aarch64_cortex-a53`, package names, packaged static ARM64 binary, required executable/assets, and emits SHA256SUMS, BUILD-IDENTITY.txt and IPK control manifests.
- Archive contents have NOT been independently downloaded/rehash-verified here; per-IPK SHA256 and actual installed dependency set remain unverified until contents inspected. No Router upload/install authority.


## Stage C runtime acceptance, operator evidence 2026-10-14
- KCHomeMainAP OpenWrt 23.05.3; new rpcd plugin SHA256 `721a034c1ebf275eceb88637b0626cf9527d7af38b469d37a669969d765f1081` matches staged IPK.
- One authorized rpcd restart completed. Immediate ubus lookup briefly returned Not found; a later read-only check confirmed rpcd running, `cdn-optimizer` exports **status only**, status returns `{"schema_version":1,"status":"not_tested","safe_to_apply":false}`; both UCI safety flags remain 0.
- Explicit negative call `ubus call cdn-optimizer scan` returned `Method not found`; it did not execute a public probe.
- Stage C rpcd basic runtime PASS. Browser console and authenticated non-admin ACL remain separate gates. No further restart authorization; **do not rerun** the operator restart script.
- New offline helper `tools/cdn_rpcd_readiness.py` performs up to 12 bounded *read-only* SSH checks (default interval 2s) with exact plugin hash and UCI fail-closed gates; focused mock tests cover immediate/delayed readiness, timeout and unsafe results. This is new GitHub-only tooling, not a rerun on Router.
- Installed `opkg status cdn-optimizer` records Depends `libc, ca-bundle` despite new staged IPK control Depends `libc, ca-bundle, jsonfilter`. Jsonfilter is installed. Track metadata drift without manual DB edits or blind reinstall; root cause not conclusively identified.

## Pending operator read-only LuCI / ACL acceptance
1. In authenticated existing admin session, open `/cgi-bin/luci/admin/services/cdn-optimizer` and child `results`, `settings` routes. Verify Overview Disabled / Not Tested, Results empty state, Settings disabled flags, and correct *Configuration unavailable* message only when UCI fetch genuinely fails.
2. Open browser DevTools Console + Network. Collect any JS exceptions, failed ubus calls and HTTP errors while navigating **without Save/Apply/Probe**. Redact cookies, session IDs, keys and authorization headers; do not export a raw HAR.
3. ACL: if an existing limited-permission account is available, open a separate private session and verify only intended read capability; use session access inspection or safe UI navigation for write denial. **Do not send a mutating UCI request as a permission test.** If no suitable user exists, mark session-level negative test BLOCKED and retain static ACL evidence.
4. Keep PR #2 Draft; no production apply, no Stage E, no merge. Every installed-vs-GitHub code delta requires separate package/redeploy authorization.


## GitHub-only final release review (2026-10-14)
**Exact opkg metadata root cause remains UNKNOWN.** Evidence proves staged IPK control declares `libc, ca-bundle, jsonfilter`, while installed opkg DB has `libc, ca-bundle`; byte-identical installed rpcd/CLI files prove payload parity, not dependency database parity. A same-version `0.1.0-1` forced reinstall with package scripts suppressed occurred, but no before/after database snapshot or isolated opkg reproducer proves which behavior retained stale Depends. Do not attribute definitively to opkg or manually edit `/usr/lib/opkg/status`. No runtime missing-dependency failure: jsonfilter exists. For the NEXT package release, increment `PKG_RELEASE` on core and LuCI, build fresh exact-head checksummed artifacts, test with a disposable offline OpenWrt opkg fixture, then request new, separate device approval before upload/install. **Do not confuse CI green with deployed parity.**

Readiness helper review: strict two-line `ubus -v list` method contract, duplicate JSON key rejection, exact fail-closed status keys/types, SHA256 and disabled UCI preflight, bounded attempts and per-command timeout. It is an **operator-invoked Python program**, not invoked in Router or in the past Windows restart script. It does NOT cure the previous restart script retroactively, and should never be used to authorize another restart. CI test doubles are not production ubus/jsonfilter equivalence.

Packaging and rollback: both staged new and old core+LuCI packages had verified SHA256 and limited permissions on Router tmpfs; tmpfs does not survive reboot. C1 backup is configuration-only (not firmware/flash snapshot), keep private. Avoid same-version package alias ambiguity, do not rely on `opkg upgrade` or version alone to select rollback. Previous install had generated default postinst/prerm hooks, suppressed deliberately during authorized Stage C. Their side effects are not validated for general production upgrades. On failure **do not auto-rollback** without explicit stage authority, especially if rpcd restart is involved.

Release gates: exact-head focused CI must be green; current physical package and rpcd acceptance refers to Artifact 11833134098/source 89d8a65 and NOT new GitHub-only readiness verifier commits; non-admin ACL real session remains BLOCKED because no non-admin account exists; browser admin smoke PASS. No router changes, public probe rerun, network apply, Stage E or merge.


## Versioned package release engineering (GitHub-only, 2026-10-14)
- New source release **0.1.0-2** for BOTH `cdn-optimizer` and `luci-app-cdn-optimizer` to avoid identical version metadata for old vs new bytes. This version is **not installed** on KCHomeMainAP. The Router remains on installed `0.1.0-1` with previously confirmed staged binary hashes.
- Offline `tests/test_cdn_release_contract.py` uses a **disposable Python in-memory package metadata fixture**, checks forward `0.1.0-1 -> 0.1.0-2` and inverse `0.1.0-2 -> 0.1.0-1` and fail-closed wrong-original-version. **This is not a real opkg execution or reproduction**. The installed dependency mismatch root cause remains UNKNOWN.
- SDK CI now independently inspects actual generated core/LuCI IPK controls for version `0.1.0-2`, expected architecture and exact dependencies. Both IPKs must be built and distributed together, with source commit, checksums and rollback identities recorded.
- **Package hooks review from last downloaded real SDK IPK `0.1.0-1`:** both Core and LuCI packages carry generated `postinst` and `prerm`. Both `postinst` scripts short-circuit on `IPKG_NO_SCRIPT=1` before sourcing `/lib/functions.sh`; both `prerm` scripts **do not** contain that guard and instead source functions and call `default_prerm` when available. A single `IPKG_NO_SCRIPT=1` setting is **not sufficient evidence** that uninstall/upgrade hooks were suppressed. Review runtime-specific `default_prerm/default_postinst` actions and obtain explicit operator approval for operational upgrade. Do not promise no restart/side effects from just the environment variable.
- Package release gates: (1) all exact-head CI green, (2) inspect fresh ZIP / dual IPKs / control and generated hooks, (3) offline isolated **real opkg** transaction test still OPEN, (4) protect UCI conffile and rollback artifacts off-router, (5) explicit separated new upload/install/restart approvals, (6) runtime verification and ACL tracking, (7) merge and Stage E approvals separately. Never auto-operate Router.


## Real opkg disposable transaction harness (GitHub-only)
- `tools/test_real_opkg_transaction.sh` invokes **the actual SDK host opkg binary** under a GitHub Actions Docker container with `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, resource limits and isolated `/work` tmpfs. Source IPKs and SDK host tools mounted read-only. The safety guard refuses execution outside a Docker/container context.
- CI pulls the **pinned** 0.1.0-1 source artifact from run `38437888881`, verifies old Core/LuCI SHA256 against known exact hashes, and builds current-head 0.1.0-2. It tests real opkg install 0.1.0-1 -> upgrade 0.1.0-2 -> explicit downgrade rollback 0.1.0-1, installed Depends metadata, and an appended config preservation marker. The fixture synthesizes only installed prerequisite package entries, *not opkg transaction behavior*.
- Hooks may run under the container's constrained filesystem even with `IPKG_NO_SCRIPT=1`; result must be interpreted using opkg console evidence, not assumed hook suppression. Any unexpected access or missing SDK host opkg binary fails CI, rather than silently substituting a Python mock.
- This harness does **not** establish real Router service reload behavior, non-admin ACL authorization, or correctness of production rollback. Root filesystem and opkg prerequisites are disposable fixtures. Review and independently verify exact-head execution result before marking the real-opkg gate passed.
