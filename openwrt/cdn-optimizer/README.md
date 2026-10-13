# CDN Optimizer — passive OpenWrt packaging scaffold

This is **not yet a working OpenWrt runtime acceptance** or functional optimizer.

- UCI `cdn_optimizer.main.enabled=0` and `allow_public_probe=0` by default.
- `/etc/init.d/cdn-optimizer` deliberately starts no background daemon.
- LuCI is a read-only overview using a fixed rpcd file-read ACL for `/tmp/cdn-optimizer/result.json`.
- The status helper prints `not_tested` if no result is present; the LuCI UI does not fabricate measurements.
- No DNS, routing, firewall, PBR, WARP, AdGuard or hosts integration.
- The Go ARM64 binaries in CI are **not yet packaged in the IPK**.
- Do not upload or install on a router before an OpenWrt SDK build, correct architecture/package dependency validation, LuCI/rpcd ACL smoke tests, rollback verification and explicit phase authorization.
- The package source must be placed inside an OpenWrt 23.05-compatible package feed; a plain GitHub Go build is not IPK verification.

## Remaining engineering gates

1. Implement a bounded, write-free one-shot runner with reliable state storage and concurrency lock.
2. Ensure rpcd JSON contract and LuCI rendering agree, including error states and permissions.
3. Package a pinned ARM64 Go binary with verifiable provenance or build it through the OpenWrt SDK; add package size checks.
4. Run actual `make package/.../compile` in a matching SDK and validate resulting IPK contents.
5. Separate offline approval from router upload, execution, active public probes and any DNS writer.
