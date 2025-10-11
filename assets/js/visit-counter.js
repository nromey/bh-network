// Client-side helper: calls our Netlify Function to increment the home visit count
// and updates the inline placeholder. Fails silently if anything goes wrong.
(function () {
  try {
    if (!window.fetch) return;
    var elTotal = document.getElementById('home-visit-total');
    var elMonth = document.getElementById('home-visit-month');
    var isDiag = (new URLSearchParams(location.search).get('diag') === '1');

    var ns = (typeof window !== 'undefined' && typeof window.BHN_COUNTER_NS === 'string' && window.BHN_COUNTER_NS) ? String(window.BHN_COUNTER_NS) : '';
    var url = '/.netlify/functions/counter-home?mode=inc'
      + (isDiag ? '&diag=1' : '')
      + (ns ? '&ns=' + encodeURIComponent(ns) : '');
    fetch(url, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var total = (typeof d.total === 'number') ? d.total : (typeof d.value === 'number' ? d.value : null);
        var month = (typeof d.month === 'number') ? d.month : null;
        if (elTotal && typeof total === 'number') elTotal.textContent = total.toLocaleString();
        if (elMonth && typeof month === 'number') elMonth.textContent = month.toLocaleString();
        if (isDiag) {
          console.log('[visit-counter]', { d, elTotal: !!elTotal, elMonth: !!elMonth, total, month });
        }
      })
      .catch(function (e) { if (isDiag) console.warn('[visit-counter] fetch error', e); });
  } catch (e) { /* ignore */ }
})();
