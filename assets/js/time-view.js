// assets/js/time-view.js
// Global time view toggle: 'net' (event-local) or 'my' (viewer-local)
(function () {
  const KEY = 'timeView:global';
  function load() {
    try {
      const v = localStorage.getItem(KEY);
      return v === 'my' ? 'my' : 'net';
    } catch (_) { return 'net'; }
  }
  function save(v) {
    try { localStorage.setItem(KEY, v); } catch (_) {}
  }
  function announce(section, view) {
    const status = section.querySelector('[data-time-view-status]');
    if (!status) return;
    if (view === 'my') {
      status.textContent = 'Showing times in your timezone.';
    } else {
      const tzName = section.dataset.tzName || '';
      const tzAbbr = section.dataset.tzAbbr || '';
      if (tzName && tzAbbr) {
        status.textContent = `Showing event times: ${tzName} (${tzAbbr}).`;
      } else if (tzName) {
        status.textContent = `Showing event times: ${tzName}.`;
      } else {
        status.textContent = 'Showing times in net timezone.';
      }
    }
  }

  function renderButtonLabels(section, view) {
    const netBtn = section.querySelector('[data-time-button="net"]');
    const myBtn = section.querySelector('[data-time-button="my"]');
    const tzSpan = netBtn ? netBtn.querySelector('[data-time-tz-label]') : null;
    if (tzSpan) {
      if (view === 'net') {
        const tzName = section.dataset.tzName || '';
        const tzAbbr = section.dataset.tzAbbr || '';
        if (tzName && tzAbbr) tzSpan.textContent = ` (${tzName}, ${tzAbbr})`;
        else if (tzName) tzSpan.textContent = ` (${tzName})`;
        else tzSpan.textContent = '';
      } else {
        tzSpan.textContent = '';
      }
    }
    // No change to My time label for now; it's concise and clear
    return { netBtn, myBtn };
  }
  function apply(view) {
    document.querySelectorAll('.home-next-nets, .nets-section').forEach((section) => {
      const btns = section.querySelectorAll('[data-time-button]');
      btns.forEach((b) => b.setAttribute('aria-pressed', b.dataset.timeButton === view ? 'true' : 'false'));
      renderButtonLabels(section, view);
      announce(section, view);
    });
    const ev = new CustomEvent('bhn:timeview-change', { detail: { view } });
    document.dispatchEvent(ev);
  }

  const initView = load();
  apply(initView);

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-time-button]');
    if (!btn) return;
    const view = btn.dataset.timeButton;
    if (view !== 'net' && view !== 'my') return;
    if (btn.getAttribute('aria-pressed') === 'true') return;
    save(view);
    apply(view);
  });

  // Update labels when tz context becomes available from hydration
  document.addEventListener('bhn:tzcontext-change', () => {
    const v = load();
    apply(v);
  });
})();
