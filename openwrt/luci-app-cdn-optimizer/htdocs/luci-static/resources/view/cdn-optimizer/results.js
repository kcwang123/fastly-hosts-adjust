'use strict';
'require view';
'require rpc';

var callStatus = rpc.declare({ object: 'cdn-optimizer', method: 'status', expect: { '': {} } });

return view.extend({
 load: function() {
  return callStatus().catch(function() { return null; });
 },
 render: function(text) {
  var state = _('No measurement recorded');
  var detail = _('Probes are disabled until separately authorized.');
  if (text) {
   try {
    var r = text;
    if (r.schema_version === 1 && r.safe_to_apply === false) {
     state = r.network_executed === true ? (r.error ? _('Failed') : _('Observed')) : _('Not tested');
     detail = _('Service: ') + String(r.service || 'unknown') +
      ' | ' + _('Timestamp: ') + String(r.started_at || 'unknown') +
      ' | ' + _('TLS verified: ') + String(!!(r.result && r.result.tls_verified));
    } else {
     state = _('Unsupported result contract');
    }
   } catch (e) {
    state = _('Invalid result JSON');
   }
  }
  return E('div', {'class':'cbi-map'}, [
   E('h2', {}, _('CDN Diagnostic Results')),
   E('p', {}, state), E('p', {}, detail),
   E('p', {}, _('Results do not authorize DNS or route changes.'))
  ]);
 },
 handleSaveApply: null,
 handleSave: null,
 handleReset: null
});
