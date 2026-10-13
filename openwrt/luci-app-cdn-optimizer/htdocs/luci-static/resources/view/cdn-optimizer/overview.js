'use strict';
'require view';
'require fs';
'require ui';

return view.extend({
 load: function() {
  // Restricted rpcd 'file.read' ACL grants access only to this exact path.
  return fs.read('/tmp/cdn-optimizer/result.json').catch(function() { return null; });
 },
 render: function(result) {
  var message = _('No active CDN measurements. No DNS changes are permitted.');
  if (result) {
   try {
    var report = JSON.parse(result);
    // Do not render arbitrary server-provided markup.
    if (report.safe_to_apply === false && report.schema_version === 1) {
     var status = report.status || 'unknown';
     if (report.network_executed === true)
      status = report.error ? 'failed' : (report.result && report.result.tls_verified === true ? 'healthy' : 'insufficient_evidence');
     else if (report.network_executed === false)
      status = 'not_tested';
     message = _('Evidence status: ') + String(status) +
      ' · ' + _('No changes authorized');
    } else {
     message = _('Untrusted or unsupported report; no changes authorized.');
    }
   } catch (e) {
    message = _('Invalid result JSON; no changes authorized.');
   }
  }
  return E('div', {'class': 'cbi-map'}, [
   E('h2', {}, _('CDN Diagnostics — read-only')),
   E('p', {}, message),
   E('p', {}, _('This view cannot launch probes, modify DNS, or apply recommendations.'))
  ]);
 },
 handleSaveApply: null,
 handleSave: null,
 handleReset: null
});
