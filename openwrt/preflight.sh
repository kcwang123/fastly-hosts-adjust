#!/bin/sh
# Read-only OpenWrt / AdGuard Home preflight. No service restarts or config writes.
set -u
say() { printf '%s\n' "$*"; }
fail=0
check() {
  label="$1"; shift
  if "$@" >/dev/null 2>&1; then say "PASS $label"; else say "FAIL $label"; fail=1; fi
}
has_section() { uci -q get "dhcp.$1" >/dev/null; }
port_matches() { [ "$(uci -q get "dhcp.dnsmasq1.port")" = "54" ]; }
agh_config() { [ -r /etc/adguardhome.yaml ] && grep -A 5 '^dns:' /etc/adguardhome.yaml | grep -q 'port: 53'; }
agh_listens() { netstat -lnut 2>/dev/null | grep -Eq '(:53[[:space:]]|:53$)'; }
dnsmasq_listens() { netstat -lnut 2>/dev/null | grep -Eq '(:54[[:space:]]|:54$)'; }
dnsmasq_dhcp() { netstat -lnu 2>/dev/null | grep -Eq '(:67[[:space:]]|:67$)'; }
say "OpenWrt Fastly preflight (read-only)"
[ -r /etc/openwrt_release ] && . /etc/openwrt_release && say "OpenWrt: ${DISTRIB_RELEASE:-unknown}"
check "dnsmasq UCI section" has_section dnsmasq1
check "LAN DHCP UCI section" has_section lan
check "dnsmasq port 54" port_matches
check "AdGuard Home configuration port 53" agh_config
check "DNS port 53 listening" agh_listens
check "DNS port 54 listening" dnsmasq_listens
check "DHCP port 67 listening" dnsmasq_dhcp
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import hashlib,http.client,ipaddress,json,socket,ssl,statistics,urllib.request,zipfile; from concurrent.futures import ThreadPoolExecutor' >/dev/null 2>&1 && say "PASS Python modules" || { say "FAIL Python modules"; fail=1; }
else
  say "INFO Python 3 not installed (needed for scanner, not for this preflight)"
fi
say "NOTE: DNS rewrites / cron are not configured by this script."
exit "$fail"
