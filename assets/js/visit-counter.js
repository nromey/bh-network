// Client-side helper: calls our Netlify Function to increment the home visit count
// and updates the inline placeholder. Fails silently if anything goes wrong.
(function () {
  try {
    var elTotal = document.getElementById('home-visit-total');
    var elMonth = document.getElementById('home-visit-month');
    if ((!elTotal && !elMonth) || !window.fetch) return;

    var url = '/.netlify/functions/counter-home?mode=inc';
    fetch(url, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var total = (typeof d.total === 'number') ? d.total : (typeof d.value === 'number' ? d.value : null);
        var month = (typeof d.month === 'number') ? d.month : null;
        if (elTotal && typeof total === 'number') elTotal.textContent = total.toLocaleString();
        if (elMonth && typeof month === 'number') elMonth.textContent = month.toLocaleString();
      })
      .catch(function () { /* ignore */ });
  } catch (e) { /* ignore */ }
})();
