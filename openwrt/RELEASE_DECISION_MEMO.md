# OpenWrt Fastly read-only adapter — Release Decision Memo
Date: 2026-10-12
Status: **NOT ACCEPTED — Draft only / no router installation**
Scope: kcwang123/fastly-hosts-adjust, PR #1

## Decision

**NO-GO** for device deployment, Cron, automatic benchmarking, DNS rewrite and
any changes to DNS/DHCP/PBR/WARP. Continue only offline CI, local simulated TLS
tests and operator-approved read-only evidence collection. A green GitHub Action
means the tested code path passed, **not** that the Router is safe to deploy to.

## What the code and CI support

- `run.sh` points to `readonly_launcher.py`; the launcher starts an isolated
  Python child with a minimal environment and checks its package manifest
  before Runner code executes.
- The source-only bundle uses an allowlist, per-file SHA-256, file inventory,
  static import checks and immediate parent-directory checks.
- Reproducible local E2E exercises two independent child processes against
  loopback TLS, rejects invalid/tampered evidence, and preserves state on failure.
- DNS transaction CLI blocks `apply` and `recover` unconditionally.
- Automatic benchmark rejects execution before AdGuard/egress evidence access.

None of these results validates the real target CDN, system CA, public exit route,
OpenWrt runtime privileges or atomic AdGuard DNS writes.

## Security review disposition

| Issue | Severity / decision | Reason |
| --- | --- | --- |
| Runtime process can rewrite bundle/parent | **NO-GO pending device verification** | Self-verification and TOCTOU are defeatable if Runtime owns writable code |
| Manifest authenticity | **Residual limitation** | Manifest and verifier come from same bundle; no independent publisher signature |
| Ancestor replacement, symlink/ACL/mount, TOCTOU | **UNKNOWN** | Immediate parent and mode checks are partial; verify whole ancestry and ACL separately |
| Dynamic Python imports and site-packages | **Residual limitation** | Static AST covers known direct/literal imports only; `-I` does not freeze system modules |
| Python runtime and system CA trust | **NOT ACCEPTED** | Device provenance/ownership and hostname-validation evidence missing |
| Big-object GitHub/Twitch benchmark | **NOT ACCEPTED** | No approved representative object proven stable and 206/Range/ETag/cache-parity suitable |
| PBR/WARP public egress | **NOT ACCEPTED** | Local routing tables are not independent proof of target-specific exit |
| AdGuard Rewrite CAS | **BLOCKED** | API Delete/Add and crash recovery cannot guarantee atomic conflict safety |
| Scheduler/Router deployment | **BLOCKED** | No operator-approved live preflight and no deployment sign-off |

## Operator evidence collection

Use `READ_ONLY_PREFLIGHT_CHECKLIST.md` only when operator independently
authorizes a device read-only review. For each gate, record observation date,
exact command/tool, redacted output, interpreter/device identity, and one of:
**PASS** = complete credible evidence meeting that invariant;
**FAIL** = demonstrably violates it;
**UNKNOWN** = absent, incomplete, stale, ambiguous or inaccessible.
UNKNOWN must never silently become PASS.

A trusted deployer must install the immutable bundle under a protected directory
that the low-privilege runtime cannot modify or replace; verify entire ancestor
ownership/modes/ACL and OS CA/system-site import sources. This is a process
trust boundary, **not an OS sandbox**.

## Engineering scope / stop conditions

Do not add Docker, IPK, sandbox frameworks, additional transaction write logic,
large benchmark test matrices or repeated CI unless a reproducible defect
necessitates them. Resume implementation only for a concrete failure with a
focused regression test. Leave PR in Draft and avoid Merge until an entirely
separate operator-approved release decision is made.
