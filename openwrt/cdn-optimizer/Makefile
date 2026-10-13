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

define Build/Compile
endef

define Package/cdn-optimizer/install
 $(INSTALL_DIR) $(1)/etc/config $(1)/etc/init.d $(1)/usr/libexec/cdn-optimizer $(1)/usr/share/rpcd/acl.d
 $(INSTALL_CONF) ./files/etc/config/cdn_optimizer $(1)/etc/config/cdn_optimizer
 $(INSTALL_BIN) ./files/etc/init.d/cdn-optimizer $(1)/etc/init.d/cdn-optimizer
 $(INSTALL_BIN) ./files/usr/libexec/cdn-optimizer/status $(1)/usr/libexec/cdn-optimizer/status
 $(INSTALL_DATA) ./files/usr/share/rpcd/acl.d/luci-app-cdn-optimizer.json $(1)/usr/share/rpcd/acl.d/luci-app-cdn-optimizer.json
endef

$(eval $(call BuildPackage,cdn-optimizer))
