'use strict';
'require view';
'require uci';

return view.extend({
 load: function() {
  return uci.load('cdn_optimizer').then(function() { return true; }).catch(function() { return false; });
 },
 render: function(loaded) {
  if (!loaded)
   return E('div', {'class':'cbi-map'}, [
    E('h2', {}, _('CDN Diagnostics Settings (read-only)')),
    E('p', {}, _('Configuration unavailable. Service status could not be verified.'))
   ]);
  var configured = uci.get('cdn_optimizer', 'main', 'enabled') === '1';
  var allowProbe = uci.get('cdn_optimizer', 'main', 'allow_public_probe') === '1';
  return E('div', {'class':'cbi-map'}, [
   E('h2', {}, _('CDN Diagnostics Settings (read-only)')),
   E('p', {}, _('Service enabled: ') + (configured ? _('Yes') : _('No'))),
   E('p', {}, _('Public probes authorized by config: ') + (allowProbe ? _('Yes') : _('No'))),
   E('p', {}, _('Configuration flags never replace the separate router execution and public-probe approval gates.'))
  ]);
 },
 handleSaveApply: null,
 handleSave: null,
 handleReset: null
});
