# Stage B — IPK upload preparation (offline only)

THIS DOCUMENT DOES NOT AUTHORIZE SSH, UPLOAD, INSTALLATION, EXECUTION, PROBE OR CONFIGURATION APPLY.
Target: user-owned KCHomeMainAP / CMCC RAX3000M. Firmware confirmed by user: OpenWrt 23.05.3 mediatek/filogic, opkg aarch64_cortex-a53.
Exact source SHA: 53c9579eb17efd3ee8f8a8828aa0a2c9e0c125fd
Actions SDK run: 38349802902; artifact ID: 11790391963; artifact name: openwrt-filogic-sdk-ipk-53c9579eb17efd3ee8f8a8828aa0a2c9e0c125fd.
Artifact ZIP is approximately 1.99MB compressed; ZIP digest is NOT an IPK digest. Individual IPK SHA256 values must be read from the artifact SHA256SUMS file.

## A. Offline artifact extraction / validation (already authorized, on Codex workstation only)

1. Authenticate with GitHub CLI using authorized repository access. Do not write credentials into logs.
2. Check git branch exact head has NOT moved, all four exact-head CI runs remain success, artifact ID/name/source identity match. If SHA differs STOP and replan.
3. On LOCAL WORKSTATION ONLY: create a private workspace, download artifact ID 11790391963 using GitHub CLI, and inspect extracted files.

    mkdir -p "$HOME/cdn-ipk-review-53c9579e"
    cd "$HOME/cdn-ipk-review-53c9579e"
    gh run download 38349802902 -R kcwang123/fastly-hosts-adjust -n openwrt-filogic-sdk-ipk-53c9579eb17efd3ee8f8a8828aa0a2c9e0c125fd
    cat BUILD-IDENTITY.txt
    sha256sum -c SHA256SUMS
    cat IPK-CONTROL.txt LUCI-IPK-CONTROL.txt
    cat IPK-CONTENTS.txt LUCI-IPK-CONTENTS.txt

4. Require exactly one core and one LuCI IPK. Inspect using ipk ar/tar tools OFFLINE; no ipk execution:
    file ./*.ipk
    ls -l ./*.ipk

5. Validate Package names exactly cdn-optimizer and luci-app-cdn-optimizer, both expected versions, core Architecture aarch64_cortex-a53 and LuCI architecture all. Verify dependencies ca-bundle / luci-base / cdn-optimizer from control fields; validate dependency versions and availability from prior read-only router inventory, not by connecting to repositories from router.
6. Verify core contains /usr/bin/fastly-public-health, /usr/libexec/cdn-optimizer/run-once, /usr/libexec/rpcd/cdn-optimizer and rpcd ACL; LuCI contains 3 views and menu. No postinst/prerm hook should trigger unapproved services, writes or scans. No wildcard shell execution, anonymous RPC write permissions, or installation auto-start.
7. Record each exact IPK filename, local SHA256, version, Architecture, Depends, unpacked file manifest and SDK source SHA in a manifest. Prefer no copy of raw system config.

## Stage B authorization prerequisite

User must explicitly authorize B UPLOAD to the single named Home Router and specify SSH destination/access method and temporary staging directory. Prior operator B0 outputs do not authorize upload.
Proposed remote staging directory: /tmp/cdn-optimizer-stage-53c9579e (temporary RAM; never overwrite existing content).
Prior /tmp available: 216.1 MiB, overlay free: 61.9 MiB. Recheck before actual authorized B; reserve memory headroom. Do not stage in /overlay or /etc.
Before transfer, confirm management path can be recovered locally and the staging directory is non-symlink, root-owned and 0700. Creating this directory is B write work, NOT B0.
Copy ONLY two verified IPKs and SHA256SUMS to remote staging. SSH/SCP transfer is B; neither installer nor probe is authorized. Never copy executable candidate separately without approval.

## B after separate explicit authorization (NOT executable yet)

Proposed bounded workflow: establish authorized SSH target; verify board/arch and free /tmp; create isolated root-owned 0700 /tmp stage; scp the exact two IPKs and SHA256SUMS; inspect file types, owner and permissions; run sha256sum -c against IPKs; cross-check source SHA and package control; report. Do not use opkg install, service reload/restart, chmod +x, probe binary, or modify live config.
Remote stage should hold only read-only files with mode 0600, root-owned. No automatic schedule, timer, daemon or network probe.
STOP if destination is wrong router, mismatching ABI or IPK digest, symlink/path collision, unexpected existing files, filesystem pressure, SSH instability, CA mismatch, dependency uncertainty or unexpected install lifecycle scripts.

## Cleanup / rollback

Offline: remove local downloaded staging copy only on user-approved workstation scope (no Router work).
Remote: deleting /tmp staging files is a separate mutating operation; obtain explicit B cleanup consent, check directory ownership and exact path, verify no active installation or process before deleting. Never recursive-delete unknown paths or existing locks. Reboot clears tmpfs but reboot itself is a separate high-impact operation, NOT an acceptable cleanup shortcut.
Stage B rollback is removal of staged copies, not package uninstall (nothing installed). Package uninstall/config recovery belongs to separately authorized C.

## GO / NO-GO before C

GO for asking C approval only if exact head+CI+artifact manifest match; both SHA256 checks pass local and remote; correct model/ABI; verified package control/dependency closure; installation scripts and rpcd ACL security reviewed; enough memory/storage; management/OOB path is credible; rollback and maintenance window documented.
NO-GO if any mismatch, unknown full dependency closure, unexplained hook, access instability, weak recovery plan, or desire to use CF_Warp as prerequisite. CF_Warp is deliberately not configured/started; it is out of MVP scope. Overlapping eth1/br-lan 192.168.1.0/24 is an observed management/routing risk, not permission to correct it.

## Codex worker copy/paste prompt

Continue kcwang123/fastly-hosts-adjust PR #2, exact GitHub head 53c9579eb17efd3ee8f8a8828aa0a2c9e0c125fd and exact SDK run 38349802902 artifact ID 11790391963. Perform STAGE A OFFLINE PREPARATION ONLY. Reconcile the live PR head, four exact-head CI runs and artifact metadata. Download only to your authorized LOCAL workspace, verify BUILD-IDENTITY and SHA256SUMS, inspect two IPK control manifests/architectures/dependencies/maintainer hooks, inventory permissions, and produce a signed-off stage B manifest and risk report. You may update feature-branch documentation/tests, following existing PR rules, but must not use Router SSH/SCP, upload, install, execute binaries, actively probe external networks, change DNS/PBR/WARP/firewall/routing or merge. Stage B upload, Stage C install/runtime, Stage D public probe and Stage E configuration apply each require distinct explicit authorization. Keep PR #1 independent, PR #2 Draft. Return exact SHA, file digest evidence, Go/No-Go and pending permissions. Do not claim package acceptance merely because CI is Green.
