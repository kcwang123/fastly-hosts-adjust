# OpenWrt read-only acceptance checklist — NOT EXECUTED

Use only in an explicitly authorized, operator-controlled shell. These commands
are for review and evidence gathering, **not approval to deploy**. No credential disclosure,
API writes, service restarts, PBR/WARP changes, cron edits or DNS rewrites.

## Device/OS and Python runtime

```sh
cat /etc/openwrt_release
uname -a
python3 -V
python3 -c 'import sys,ssl,sysconfig,http.client,socket,ipaddress,json,statistics;print(sys.version);print(ssl.OPENSSL_VERSION);print(ssl.get_default_verify_paths());print(sysconfig.get_paths().get("purelib"))'
df -k /overlay
```

Review: release/architecture, interpreter availability, default CA file/directory,
installed-module import directories, free persistent storage. Treat the CA origin
and its file ownership/permissions as unresolved until verified. Do not export
`SSL_CERT_FILE` / `PYTHONPATH` to satisfy a test.

## DNS/DHCP evidence, strictly read-only

```sh
uci -q show dhcp
netstat -lnut
ip -4 route show
ip -4 rule show
```

Review: AdGuard listener on DNS 53, dnsmasq 54 and DHCP 67, LAN binding,
PBR rules, and any tunnel routes. Do not change them.

## WARP/PBR evidence

```sh
ip -4 address show
ip -4 route show table all
ip -4 rule show
```

The commands above show only local routing intentions. They **do not** independently
prove which public exit a TLS flow to a particular CDN IP actually used.
Therefore public-egress attestation remains NOT ACCEPTED. Avoid printing tokens,
secrets or private key contents into logs or tickets.

## Runtime package checks — local workstation/CI only

```sh
review_parent="$(mktemp -d)"
python openwrt/build_readonly_bundle.py --source openwrt --output "$review_parent/fastly-readonly-review"
python -c 'import sys;sys.path.insert(0,"openwrt");from build_readonly_bundle import verify;print(verify(sys.argv[1]))' "$review_parent/fastly-readonly-review"
```

No automated installer is approved. Only `readonly_launcher.py` is a supported
Runtime entrypoint; `run.sh` references that launcher but must **not** be
installed into Cron. Direct invocation of `runner.py` bypasses the optional
environment cleaning and is unsupported.

## Explicit blockers

- CDN source object: independently verify stable sufficient size, 206 Range,
  Content-Range / Content-Length, ETag and Cache on both routes.
- Egress: obtain independently corroborated target-specific public routing
  attestation (not just local `ip route`).
- CA: verify OS trust store provenance, permissions and TLS hostname validation.
- DNS: AdGuard rewrite lacks compare-and-swap; **writes remain BLOCKED**.
- Deployment and Cron: **NOT ACCEPTED**.

Do not record PASS from missing evidence or from CI-only localhost tests.

## Strict evidence grading — every field must be classified

Use **PASS** only when the operator supplied a fresh, complete observation and
it satisfies the exact documented invariant; **FAIL** when a supplied observation
demonstrably violates an invariant; **UNKNOWN** when absent, stale, ambiguous,
redacted beyond interpretation, or the command/tool is unavailable. Neither
UNKNOWN nor FAIL authorizes installation, Cron, Benchmark or DNS modification.

| Gate | PASS | FAIL | UNKNOWN |
| --- | --- | --- | --- |
| OS and Python | OpenWrt release, architecture, Python 3, standard ssl/http.client modules verified | Interpreter missing or essential module fails to import | No current OS/runtime output |
| System TLS roots | Default CA path exists, readable, ownership and modification history acceptable to operator, verified hostname check enabled | CA absent, writable by untrusted user, or hostname verification disabled | CA origin or permissions not inspected |
| Local DNS/DHCP | Listener evidence matches intended AdGuard :53, dnsmasq :54 and DHCP :67 without conflicts | Missing or conflicting listeners | Listener process ownership / port binding unconfirmed |
| Storage | Persistent overlay has >=10 MiB free from contemporaneous `df -k /overlay` | Below 10 MiB | Storage not measured or device not mounted |
| Runtime bundle | Exact SHA-256, symlink/file list and import check passes before launch in restricted launcher | Any mismatch or unexpected module | Only CI build verified; device artifact unexamined |
| Target CDN | Both address pairs give verified 206 Range/Length, consistent ETag/cache and sufficient stable object | Content mismatch, truncated response or inconsistent metadata | No verified target-specific object/headers |
| PBR/WARP | Independently corroborated public egress for each target destination on actual device | Observed public egress differs from required route | Only local route/rule observations available |
| AdGuard atomic write | Atomic compare-and-swap/recovery design independently implemented and proven | Delete/Add race or external override demonstrated | No trusted CAS support; deployment decision remains BLOCKED |

**Current device observations: UNKNOWN. Release acceptance: NOT ACCEPTED.**
No commands in this checklist have been executed against the router in this
engineering session. The DNS write policy is BLOCKED even if a future report
marks other gates PASS.

## Deployment ownership / trusted code boundary — REQUIRED, NOT EXECUTED

Before a future deployment can be accepted, record (without changing the router):
```sh
id
ls -ld /usr/lib/fastly-optimizer /etc/fastly-optimizer
ls -l /usr/lib/fastly-optimizer
python3 -c 'import sys,site,ssl;print(sys.path);print(site.getsitepackages() if hasattr(site,"getsitepackages") else "unknown");print(ssl.get_default_verify_paths())'
```
Sanitize any path names that disclose private user information before sharing.
**PASS** requires a reviewed separate deployment owner for immutable source
files and a less-privileged runtime identity with no write permission to the
bundle directory, ancestors permitting replacement, launcher, manifest, modules
or installed Python import paths. Filesystem capabilities/ACLs/overlay mounts
must be inspected independently; POSIX mode bits alone are insufficient.
**FAIL** if runtime can write or replace executable code or its trust manifest.
**UNKNOWN** if runtime identity, directory ancestry, ACLs, mounts or module
owners have not been checked.

System Python/site-packages and OS CA trust remain external trust roots even
when `python -I` is used. `-I` reduces environment and user-site influence
but cannot establish a sandbox, freeze the system interpreter or eliminate
check-then-import TOCTOU. Do not treat a self-signed package manifest as an
independently authenticated provenance statement.

TLS default trust-path output alone is **UNKNOWN**, not PASS, until package
provenance, owner permissions, roots and hostname-verification behaviour are
reviewed. The certificate store must not be overridden with an untrusted
`SSL_CERT_FILE` or similar variable.

No real device commands have been run; this is a checklist only.

## Parent-directory replacement gate (2026-10-12 review)

The bundle verifier now rejects a symlinked immediate parent or an immediate
parent writable by group/other users. The CI artifact is built beneath a private
temporary parent to exercise this invariant. This is a narrowly scoped defence
against package-directory replacement, not proof of immutable deployment.

For a real device, inspect the complete ancestor chain as well as ACLs and
ownership independently. **PASS** requires a separate trusted deployment owner,
a runtime principal without permission to alter the package *or rename any
ancestor*, and an acceptable device-specific system Python/CA trust chain.
**FAIL** if an untrusted runtime can replace the package, modify its verifier
or tamper with interpreter/module roots. **UNKNOWN** where identities, access
rights, filesystem mount behaviour or CA provenance are unobserved. These
conditions remain UNKNOWN; no Router inspection was performed.

Docker, containers and IPK are **not prerequisites** for this read-only
prototype: introduce them only if a later concrete deployment requirement
cannot be satisfied by a protected directory and restricted process identity.
The current scope does not justify additional packaging machinery. Continue to
block all DNS writes because AdGuard has no atomic CAS.
