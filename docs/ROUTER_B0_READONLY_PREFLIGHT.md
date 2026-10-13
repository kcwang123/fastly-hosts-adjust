# Router B0 — Read-only Preflight and Codex Handoff

Status: OFFLINE PREPARATION ONLY. No Router SSH authorization is granted by this document.
Target: Home OpenWrt device, identity and firmware unknown until authorized inspection. Do not conflate Home with Church / Office.
PR #2 source baseline: cd9df7b5cc15c8000c2d44b276bd0300c12dbc46; SDK Artifact ID 11789102172.

## Authorization boundaries

A Offline: authorized; B0 Router read-only: requires separate explicit approval, target and access scope;
B Upload, C Installation/Execution, D Public Probe, E DNS/Route/Firewall/PBR/WARP Apply: each requires separate approval.
Never treat B0 success as authorization for B/C/D/E. Do not run Router commands during document preparation.

## B0 command inventory — BusyBox ash, read-only; do NOT run before B0 approval

Device/ABI:
    ubus call system board
    uname -m
    uname -r
    cat /etc/openwrt_release
    opkg print-architecture
    busybox | head -n 2

RAM/flash/CA:
    free
    cat /proc/meminfo | head -n 12
    df -h / /tmp /overlay
    mount | grep -E ' /overlay | /tmp '
    ls -ld /tmp /overlay /etc/ssl/certs 2>/dev/null
    ls -l /etc/ssl/cert.pem /etc/ssl/certs/ca-certificates.crt 2>/dev/null
    opkg list-installed ca-bundle
    opkg list-installed ca-certificates

Services and dependencies:
    opkg list-installed rpcd
    opkg list-installed uhttpd
    opkg list-installed luci-base
    opkg list-installed luci-mod-admin-full
    opkg list-installed pbr
    opkg list-installed luci-app-pbr
    opkg list-installed adguardhome
    opkg list-installed cloudflared
    ubus list
    ps w | grep -E '[r]pcd|[u]httpd|[a]dguard|[c]loudflared|[w]arp|[p]br'

Routing context, NO active probes:
    ip -4 rule show
    ip -4 route show table main
    ip -6 rule show
    ip -6 route show table main
    ls -ld /tmp/cdn-optimizer /tmp/cdn-optimizer.lock /usr/libexec/rpcd /usr/share/rpcd/acl.d 2>/dev/null
    opkg list-installed cdn-optimizer
    opkg list-installed luci-app-cdn-optimizer

No ping, traceroute, curl, wget, DNS resolution, packet probes, UCI writes, opkg install, service restart, package execution, uploaded scripts or binary execution.
An unavailable command means UNKNOWN, not a reason to install tooling.
Do not print entire UCI packages, secret-bearing environment, credentials, key material, SSID, DHCP client inventories or auth tokens.
Redact private route addresses and sensitive service details before including evidence in GitHub.

## Evidence matrix

| Domain | Minimum evidence | GO prerequisite | NO-GO |
| --- | --- | --- | --- |
| Ownership/target | Approved environment/device/SSH role | Explicit B0 permission and recovery path | Ambiguous host or absent approval |
| ABI | board, release, uname, opkg arch | Match mediatek/filogic + aarch64_cortex-a53 and compatible firmware | Mismatch / unknown |
| Resources | free, df, tmp, overlay | Sufficient RAM/flash headroom | Pressure or unknown sizing |
| CA | CA files and package inventory | Trust store plausible; runtime TLS still pending | Missing CA |
| rpcd/LuCI | package versions, ubus availability | Supported service infrastructure | Missing/incompatible |
| DNS/PBR/WARP | package and policy routing evidence | Ownership and egress path documented | Unknown management/routing boundary |
| Recovery | OOB/local access, rollback owner | Approved recovery and prospective maintenance plan | Remote lockout risk |

## Failure domains and gates

Management-plane lockout; ABI mismatch; overlay/RAM pressure; rpcd service account and ACL behavior;
LuCI menu/session permissions; AdGuard/dnsmasq/PBR/WARP DNS or route ownership; CA/HTTPS trust;
stale /tmp state/lock. None are considered runtime verified by SDK CI alone.
Go at B0 means eligible to request separate B Upload authorization; never automatic install/probe.
No-Go on unknown ownership, unsupported target, resource shortage, missing rollback access, or evidence conflict.
Do not create backups, remove locks or clean state on Router during B0: those write to device.

## Redacted output checkpoint

Record environment, approval reference, board, firmware, opkg ABI, RAM/tmp/overlay, CA, rpcd/LuCI,
AdGuard/PBR/WARP owners, IPv4/IPv6 policy route summary, access/recovery readiness,
Verified / Inferred / Unknown, No-Go findings, decision, and separately required authorization.

## Ready-to-use Codex Worker Prompt

Continue kcwang123/fastly-hosts-adjust PR #2 from exact head cd9df7b5cc15c8000c2d44b276bd0300c12dbc46.
Read docs/ROUTER_B0_READONLY_PREFLIGHT.md and docs/CODEX_ROUTER_HANDOFF.md. Verify prior GitHub
four green checks and artifact ID 11789102172. For this turn OFFLINE ONLY: do not SSH, upload, install,
execute binaries, probe public networks or apply network settings. Prepare explicit B0 read-only checklists,
redacted evidence capture, Go/No-Go matrix and rollback prerequisites. After the user separately grants B0
and confirms Home Router identity/management route, run only bounded read-only commands described here.
Stop at B0. Never advance to B/C/D/E without independent authorization. Preserve PR #1 separately and PR #2 Draft.
