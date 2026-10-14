#!/bin/sh
# Execute INSIDE disposable network-disabled container only.
set -eu
: "${OLD_CORE:?}" "${OLD_LUCI:?}" "${NEW_CORE:?}" "${NEW_LUCI:?}" "${OPKG_BIN:?}"
[ "$(id -u)" -eq 0 ] || exit 30
[ -e /run/.containerenv ] || [ -e /.dockerenv ] || { echo 'REFUSE_NON_CONTAINER'; exit 31; }
command -v "${OPKG_BIN}" >/dev/null 2>&1 || { echo 'OPKG_UNAVAILABLE'; exit 32; }
mkdir -p /work/root/usr/lib/opkg /work/root/etc/opkg /work/root/etc/config /work/root/var/lock /work/root/tmp
# Only fake base image prereqs; transactions themselves are executed by actual opkg.
cat > /work/root/usr/lib/opkg/status <<'EOF'
Package: libc
Version: 1.2.4-4
Architecture: aarch64_cortex-a53
Status: install ok installed

Package: ca-bundle
Version: 20230311-1
Architecture: all
Status: install ok installed

Package: jsonfilter
Version: 2024-01-23-594cfa86-1
Architecture: aarch64_cortex-a53
Status: install ok installed

Package: luci-base
Version: git-24.086.45142-09d5a38
Architecture: all
Status: install ok installed

EOF
cat > /work/opkg.conf <<'EOF'
dest root /
lists_dir ext /work/lists
arch all 1
arch noarch 1
arch aarch64_cortex-a53 10
EOF
mkdir -p /work/lists
opkg() { "${OPKG_BIN}" -f /work/opkg.conf -o /work/root "$@"; }
# Fail closed if the actual opkg resolver cannot see disposable image prerequisites.
for pkg in libc ca-bundle jsonfilter luci-base; do
  opkg status "$pkg" | grep -F 'Status: install ok installed' >/dev/null || {
    echo "FIXTURE_PREREQUISITE_INVISIBLE: $pkg"
    exit 39
  }
done
logstatus() {
  opkg status cdn-optimizer > "/work/$1-core.status"
  opkg status luci-app-cdn-optimizer > "/work/$1-luci.status"
}
assert_field() { grep -Fx "$2" "$1" >/dev/null || { echo "ASSERT_FAIL $1: $2"; exit 41; }; }
# old initial installation, inside network-disabled disposable container.
IPKG_NO_SCRIPT=1 opkg install "${OLD_CORE}" "${OLD_LUCI}"
logstatus old
assert_field /work/old-core.status 'Version: 0.1.0-1'
assert_field /work/old-core.status 'Depends: libc, ca-bundle'
# Preserve custom UCI content, verify upgrade/rollback does not clobber.
cfg=/work/root/etc/config/cdn_optimizer
test -f "$cfg" || { echo 'CONFIG_MISSING'; exit 42; }
printf '\n# harness-preserve-marker-8234\n' >> "$cfg"
sha="$(sha256sum "$cfg" | cut -d' ' -f1)"
IPKG_NO_SCRIPT=1 opkg install "${NEW_CORE}" "${NEW_LUCI}"
logstatus upgraded
assert_field /work/upgraded-core.status 'Version: 0.1.0-2'
assert_field /work/upgraded-core.status 'Depends: libc, ca-bundle, jsonfilter'
assert_field /work/upgraded-luci.status 'Version: 0.1.0-2'
grep -F '# harness-preserve-marker-8234' "$cfg" >/dev/null || { echo 'UPGRADE_CONFIG_LOST'; exit 43; }
# Capture config outside package root BEFORE downgrade (explicit rollback preparation).
cp "$cfg" /work/rollback-config.snapshot
test "$(sha256sum /work/rollback-config.snapshot | cut -d' ' -f1)" = "$sha" || exit 45
# Downgrade requires explicit force-downgrade; not automatic recovery.
IPKG_NO_SCRIPT=1 opkg --force-downgrade install "${OLD_CORE}" "${OLD_LUCI}"
logstatus rollback
assert_field /work/rollback-core.status 'Version: 0.1.0-1'
assert_field /work/rollback-core.status 'Depends: libc, ca-bundle'
assert_field /work/rollback-luci.status 'Version: 0.1.0-1'
grep -F '# harness-preserve-marker-8234' "$cfg" >/dev/null || { echo 'ROLLBACK_CONFIG_LOST'; exit 44; }
printf 'REAL_OPKG_TRANSACTION_PASS\n'
