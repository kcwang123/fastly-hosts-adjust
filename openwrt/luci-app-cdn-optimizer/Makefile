include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-cdn-optimizer
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKGARCH:=all

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-cdn-optimizer
 SECTION:=luci
 CATEGORY:=LuCI
 SUBMENU:=3. Applications
 TITLE:=Read-only CDN diagnostics views
 DEPENDS:=+cdn-optimizer +luci-base
 PKGARCH:=all
endef

define Build/Compile
endef

define Package/luci-app-cdn-optimizer/install
	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/cdn-optimizer
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./htdocs/luci-static/resources/view/cdn-optimizer/*.js $(1)/www/luci-static/resources/view/cdn-optimizer/
	$(INSTALL_DATA) ./root/usr/share/luci/menu.d/luci-app-cdn-optimizer.json $(1)/usr/share/luci/menu.d/
endef

$(eval $(call BuildPackage,luci-app-cdn-optimizer))
