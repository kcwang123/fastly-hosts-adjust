#!/bin/sh
# Router preflight only: no installation, mutation, DHCP restart, or cron setup.
set -eu
echo "OpenWrt Fastly deployment preflight (read only)"
fail=0
check() {
  label="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS $label"; else echo "FAIL $label"; fail=1; fi
}
has_file() { [ -r "$1" ]; }
has_dns() { netstat -lnut 2>/dev/null | grep -Eq '(:53[[:space:]]|:53$)'; }
has_dhcp() { netstat -lnu 2>/dev/null | grep -Eq '(:67[[:space:]]|:67$)'; }
dnsmasq_port() { [ "$(uci -q get dhcp.dnsmasq1.port)" = "54" ]; }
python_modules() {
  python3 -c 'import ssl,socket,http.client,ipaddress,json,statistics,urllib.request,concurrent.futures' 
}
overlay() {
  df -k /overlay | awk 'NR==2{exit !($4>=10240)}'
}
check "OpenWrt release" has_file /etc/openwrt_release
check "AdGuard persistent config" has_file /etc/adguardhome.yaml
check "AdGuard DNS listener 53" has_dns
check "DHCP listener 67" has_dhcp
check "dnsmasq port 54" dnsmasq_port
check "Python standard modules" python_modules
check "overlay >=10MiB available" overlay
echo "NOTE: No cron installed, DNS rewrite performed, service restarted, or files changed."
exit "$fail"
