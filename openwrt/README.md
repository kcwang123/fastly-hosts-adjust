# OpenWrt integration (work in progress)

This fork retains the upstream Fastly scanner. The OpenWrt integration will run on the router but must **not** call upstream `apply`: it writes `/etc/hosts`, whereas LAN clients use AdGuard Home DNS.

## Verified target environment

- OpenWrt 23.05.3, aarch64 (Mediatek Filogic), 61.9 MiB free overlay as initially observed.
- AdGuard Home v0.107.36 listening TCP/UDP :53; web UI :3000.
- dnsmasq listening TCP/UDP :54 and DHCP UDP :67.
- AdGuard forwards `.lan` to `127.0.0.1:54`, upstream Quad9 DoH.
- Working local record: KCHomeMainAP.lan → 192.168.1.240.

## First deployment gate

Copy `openwrt/preflight.sh` to router, then run `sh preflight.sh`. It **only reads** configuration, port listeners and Python module availability. It does not alter DNS, DHCP, firewall, PBR, hosts, cron or AdGuard.

## Planned implementation

1. Confirm Python stdlib module availability and scanner egress path (PBR/WARP).
2. Refactor scanner into test-only candidate JSON output without touching hosts.
3. Verify candidate domain-to-IP mapping, HTTPS SNI/certificate, and speed improvement.
4. Implement AdGuard Home DNS Rewrite API adapter with explicit managed-domain ownership, snapshot-before-write, dry-run, rollback, and authenticated local API access.
5. Add three-hour lightweight health check; full benchmark daily or on degraded health, never concurrent. Ensure fail-open by removing only managed rewrites if necessary.
6. Enable cron only after router smoke test and DNS verification. Never manage unrelated AdGuard rewrites.

## Operational cautions

- Upstream full benchmark can use ~360 MB per run with all service families enabled. Eight full runs/day would be ~2.88 GB/day; schedule health checks instead.
- AdGuard workdir is /var/adguardhome → /tmp/adguardhome (volatile). Keep credentials out of scripts, logs and git.
- Do not restart dnsmasq unnecessarily. Its DHCP service is required for LAN availability.
- This branch has **no production DNS write path** and is not ready for automated rollout.
