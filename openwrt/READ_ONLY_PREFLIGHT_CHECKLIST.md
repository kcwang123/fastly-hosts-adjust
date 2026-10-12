# OpenWrt read-only acceptance checklist — NOT EXECUTED

Use only in an explicitly authorized, operator-controlled shell. These commands
are for review and evidence gathering, **not approval to deploy**. No credentials,
API writes, service restarts, PBR/WARP changes, cron edits or DNS rewrites.

## Device/OS and Python runtime

```sh
cat /etc/openwrt_release
uname -a
python3 -V
python3 -c 'import sys,ssl,sysconfig;print(sys.version);print(ssl.OPENSSL_VERSION);print(ssl.get_default_verify_paths());print(sysconfig.get_paths().get("purelib"))'
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
python openwrt/build_readonly_bundle.py --source openwrt --output /tmp/fastly-readonly-review
python -c 'import sys;sys.path.insert(0,"openwrt");from build_readonly_bundle import verify;print(verify("/tmp/fastly-readonly-review"))'
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
