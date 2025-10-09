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
      status.textContent = showUTC ? 'Showing local time (UTC also shown).' : 'Showing times in your timezone.';
    } else {
      const tzName = section.dataset.tzName || '';
      const tzAbbr = section.dataset.tzAbbr || '';
      if (tzName && tzAbbr) {
        status.textContent = showUTC ? `Showing event times: ${tzName} (${tzAbbr}); UTC also shown.` : `Showing event times: ${tzName} (${tzAbbr}).`;
      } else if (tzName) {
        status.textContent = showUTC ? `Showing event times: ${tzName}; UTC also shown.` : `Showing event times: ${tzName}.`;
      } else {
        status.textContent = showUTC ? 'Showing times in net timezone; UTC also shown.' : 'Showing times in net timezone.';
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

  // Also handle clicks on the label to guarantee toggling in all browsers/layouts
  document.addEventListener('click', (e) => {
    const label = e.target.closest('label.time-utc-toggle');
    if (!label) return;
    const input = label.querySelector('[data-time-utc-toggle]');
    if (!input) return;
    e.preventDefault();
    input.checked = !input.checked;
    // Dispatch a change event so the central handler persists + applies
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  // Update labels when tz context becomes available from hydration
  document.addEventListener('bhn:tzcontext-change', () => {
    const v = load();
    // Refresh labels/status without rebroadcasting the timeview-change event
    apply(v, { silent: true });
  });
})();
