# OpenWrt CDN Optimizer — offline packaging status

Current package is a **read-only diagnostic integration candidate**, not router-accepted.

- Passive `/etc/init.d/cdn-optimizer`: does not start any service or scan.
- UCI defaults: `enabled=0`, `allow_public_probe=0`.
- Manual `/usr/libexec/cdn-optimizer/run-once --manual-public-probe-authorized` requires two explicit UCI flags as well as an explicit operator argument. **Do not invoke on a router without separate execution and public-probe authorization.**
- One-shot uses a non-overlap mkdir lock (`/tmp/cdn-optimizer.lock`), bounded CLI (max 65536 requested bytes), single-result temporary file and atomic same-filesystem rename to `/tmp/cdn-optimizer/result.json`. Failed probe removes stale result. Stale lock requires manual inspection.
- The read-only rpcd exec plugin exposes `status` only. LuCI offers Overview, Results and Settings, with no apply or scan controls.
- The Go candidate IP/TLS/host allowlist is independent of the UCI selection; never treat entered IP as ownership/POP evidence.
- All status is temporary under `/tmp` (RAM), not persistent flash history.

## SDK packaging gate (not yet executed)

The package Makefile deliberately rejects builds without `CDN_OPTIMIZER_BIN` and `CDN_OPTIMIZER_SHA256`. When using an OpenWrt **23.05.3 SDK matched to the actual target subtarget and package ABI**, stage the verified linux/arm64 `fastly-public-health` artifact and provide its matching SHA256 to the make invocation. Cross-compiled Go ARM64 ELF is **not** itself proof of SDK/IPK or target compatibility.

Still required:
1. Validate exact router `opkg print-architecture`, `uname -m`, libc/CA and free RAM/storage through an approved read-only preflight.
2. Use a matching SDK and run the package compile, inspect IPK metadata/files/permissions and dependency closure; make sure `luci-app-cdn-optimizer` package builds and resolves.
3. Validate rpcd file/ubus ACL behavior and LuCI interactions in a non-production image or approved Router phase.
4. Test lock stale/recovery, output failure behavior, limited resource budgets and lifecycle on actual BusyBox ash; static CI is not runtime proof.
5. Verify that the artifact is statically linked or otherwise compatible, and that firmware contains appropriate CA certificates.
6. No DNS, PBR, WARP, hosts or network setting writer is authorized.

## Rollback boundary

Only after separately authorized installation: disable the package, remove installed IPKs, and clean its `/tmp/cdn-optimizer` state and lock **after confirming no scan is running**. Preserve existing DNS, firewall and routing configurations. Do not run cleanup as part of GitHub-side work.
