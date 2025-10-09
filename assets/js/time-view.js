// assets/js/time-view.js
// Global time view toggle: 'net' (event-local) or 'my' (viewer-local)
(function () {
  const KEY = 'timeView:global';
  const UTC_KEY = 'timeView:showUTC';
  function load() {
    try {
      const v = localStorage.getItem(KEY);
      return v === 'my' ? 'my' : 'net';
    } catch (_) { return 'net'; }
  }
  function save(v) {
    try { localStorage.setItem(KEY, v); } catch (_) {}
  }
  function loadUTC() {
    try { return localStorage.getItem(UTC_KEY) === '1'; } catch (_) { return false; }
  }
  function saveUTC(on) {
    try { localStorage.setItem(UTC_KEY, on ? '1' : '0'); } catch (_) {}
  }
  function announce(section, view) {
    const status = section.querySelector('[data-time-view-status]');
    if (!status) return;
    const showUTC = loadUTC();
    if (view === 'my') {
      status.textContent = showUTC ? 'Local time and UTC shown.' : 'Local time.';
      return;
    }
    // Net time
    const tzName = section.dataset.tzName || '';
    const tzAbbr = section.dataset.tzAbbr || '';
    let base = 'Net time';
    if (tzName && tzAbbr) base = `Net time (${tzName}, ${tzAbbr})`;
    else if (tzName) base = `Net time (${tzName})`;
    status.textContent = showUTC ? `${base} and UTC shown.` : `${base}.`;
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
  function apply(view, options = {}) {
    const { silent = false } = options;
    document.querySelectorAll('.home-next-nets, .nets-section').forEach((section) => {
      const btns = section.querySelectorAll('[data-time-button]');
      btns.forEach((b) => b.setAttribute('aria-pressed', b.dataset.timeButton === view ? 'true' : 'false'));
      // Sync UTC checkbox
      const utcToggle = section.querySelector('[data-time-utc-toggle]');
      if (utcToggle) {
        try { utcToggle.checked = !!loadUTC(); } catch (_) {}
      }
      renderButtonLabels(section, view);
      announce(section, view);
    });
    if (!silent) {
      const ev = new CustomEvent('bhn:timeview-change', { detail: { view } });
      document.dispatchEvent(ev);
    }
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

  // Listen for UTC checkbox toggles (global preference)
  document.addEventListener('change', (e) => {
    const chk = e.target.closest('[data-time-utc-toggle]');
    if (!chk) return;
    saveUTC(!!chk.checked);
    // Re-apply current view to update status text and hydrate additions
    apply(load());
  });

  // Rely on native checkbox interactions (click/space) + change handler above

  // Update labels when tz context becomes available from hydration
  document.addEventListener('bhn:tzcontext-change', () => {
    const v = load();
    // Refresh labels/status without rebroadcasting the timeview-change event
    apply(v, { silent: true });
  });
})();
