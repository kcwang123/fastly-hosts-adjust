include $(TOPDIR)/rules.mk

PKG_NAME:=cdn-optimizer
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/cdn-optimizer
 SECTION:=net
 CATEGORY:=Network
 TITLE:=Read-only CDN diagnostic preflight
 DEPENDS:=+ca-bundle
endef

define Package/cdn-optimizer/description
 Disabled-by-default diagnostic scaffolding; no automatic public probes or DNS changes.
endef

CDN_OPTIMIZER_BIN?=
CDN_OPTIMIZER_SHA256?=

define Build/Compile
	@test -n "$(CDN_OPTIMIZER_BIN)" || { echo "missing CDN_OPTIMIZER_BIN"; exit 1; }
	@test -n "$(CDN_OPTIMIZER_SHA256)" || { echo "missing CDN_OPTIMIZER_SHA256"; exit 1; }
	@test -f "$(CDN_OPTIMIZER_BIN)" || { echo "missing staged binary"; exit 1; }
	@printf '%s  %s\n' "$(CDN_OPTIMIZER_SHA256)" "$(CDN_OPTIMIZER_BIN)" | sha256sum -c -
endef

define Package/cdn-optimizer/install
 $(INSTALL_DIR) $(1)/etc/config $(1)/etc/init.d $(1)/usr/bin $(1)/usr/libexec/cdn-optimizer $(1)/usr/share/rpcd/acl.d
 $(INSTALL_BIN) $(CDN_OPTIMIZER_BIN) $(1)/usr/bin/fastly-public-health
 $(INSTALL_CONF) ./files/etc/config/cdn_optimizer $(1)/etc/config/cdn_optimizer
 $(INSTALL_BIN) ./files/etc/init.d/cdn-optimizer $(1)/etc/init.d/cdn-optimizer
 $(INSTALL_BIN) ./files/usr/libexec/cdn-optimizer/status $(1)/usr/libexec/cdn-optimizer/status
 $(INSTALL_DATA) ./files/usr/share/rpcd/acl.d/luci-app-cdn-optimizer.json $(1)/usr/share/rpcd/acl.d/luci-app-cdn-optimizer.json
endef

$(eval $(call BuildPackage,cdn-optimizer))
