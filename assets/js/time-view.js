// assets/js/time-view.js
// Global time view toggle: 'net' (event-local) or 'my' (viewer-local)
(function () {
  const DEFAULT_TZ_IANA = 'America/New_York'; // BHN standard net time
  const KEY = 'timeView:global';
  const UTC_KEY = 'timeView:showUTC';
  function localAbbr() {
    try {
      const parts = new Intl.DateTimeFormat('en-US', { timeZoneName: 'short' }).formatToParts(new Date());
      const part = parts.find(p => p.type === 'timeZoneName');
      return part ? String(part.value).toUpperCase() : '';
    } catch (_) { return ''; }
  }
  function localLong() {
    try {
      const partsGeneric = (() => {
        try { return new Intl.DateTimeFormat('en-US', { timeZoneName: 'longGeneric' }).formatToParts(new Date()); }
        catch (_) { return null; }
      })();
      let part = partsGeneric ? partsGeneric.find(p => p.type === 'timeZoneName') : null;
      if (!part) {
        try {
          const parts = new Intl.DateTimeFormat('en-US', { timeZoneName: 'long' }).formatToParts(new Date());
          part = parts.find(p => p.type === 'timeZoneName');
        } catch (_) { part = null; }
      }
      return part ? String(part.value) : '';
    } catch (_) { return ''; }
  }
  function tzAbbrFor(iana) {
    try {
      if (!iana) return '';
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'short' }).formatToParts(new Date());
      const part = parts.find(p => p.type === 'timeZoneName');
      return part ? String(part.value).toUpperCase() : '';
    } catch (_) { return ''; }
  }
  function tzLongFor(iana) {
    try {
      if (!iana) return '';
      const d = new Date();
      let part = null;
      try { part = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'longGeneric' }).formatToParts(d).find(p => p.type === 'timeZoneName'); }
      catch (_) { /* ignore */ }
      if (!part) {
        try { part = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'long' }).formatToParts(d).find(p => p.type === 'timeZoneName'); }
        catch (_) { part = null; }
      }
      return part ? String(part.value) : '';
    } catch (_) { return ''; }
  }
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
    const showAbbr = String(section.dataset.tzShowAbbr || 'true') !== 'false';
    const showLabel = String(section.dataset.tzShowLabel || 'true') !== 'false';
    if (!showLabel) {
      const base = view === 'my' ? 'My time' : 'Net time';
      status.textContent = loadUTC() ? `${base} and UTC shown.` : `${base}.`;
      return;
    }
    if (view === 'my') {
      const long = localLong();
      const abbr = localAbbr();
      const base = showAbbr
        ? ((long && abbr) ? `My time (${long} (${abbr}))` : (abbr ? `My time (${abbr})` : (long ? `My time (${long})` : 'My time')))
        : (long ? `My time (${long})` : 'My time');
      status.textContent = showUTC ? `${base} and UTC shown.` : `${base}.`;
      return;
    }
    // Net time
    let tzName = section.dataset.tzName || '';
    let tzAbbr = section.dataset.tzAbbr || '';
    const forceIanaAnn = section.dataset.tzForceIana || '';
    if (forceIanaAnn) {
      tzName = tzLongFor(forceIanaAnn) || tzName;
      tzAbbr = tzAbbrFor(forceIanaAnn) || tzAbbr;
    }
    let base = 'Net time';
    if (!tzName && !tzAbbr && section.classList.contains('home-next-nets')) {
      // Fallback to BHN standard net time on Next Net block
      const fallbackLong = tzLongFor(DEFAULT_TZ_IANA);
      const fallbackAbbr = tzAbbrFor(DEFAULT_TZ_IANA);
      tzName = fallbackLong || tzName;
      tzAbbr = fallbackAbbr || tzAbbr;
    }
    let labeled = false;
    if (showAbbr) {
      if (tzName && tzAbbr) { base = `Net time (${tzName} (${tzAbbr}))`; labeled = true; }
      else if (tzAbbr) { base = `Net time (${tzAbbr})`; labeled = true; }
      else if (tzName) { base = `Net time (${tzName})`; labeled = true; }
    } else {
      if (tzName) { base = `Net time (${tzName})`; labeled = true; }
    }
    if (!labeled) base = 'Net time (varies)';
    status.textContent = showUTC ? `${base} and UTC shown.` : `${base}.`;
  }

  function renderButtonLabels(section, view) {
    const netBtn = section.querySelector('[data-time-button="net"]');
    const myBtn = section.querySelector('[data-time-button="my"]');
    const showAbbr = String(section.dataset.tzShowAbbr || 'true') !== 'false';
    const showLabel = String(section.dataset.tzShowLabel || 'true') !== 'false';
    const tzSpan = netBtn ? netBtn.querySelector('[data-time-tz-label]') : null;
    if (tzSpan) {
      if (!showLabel) { tzSpan.textContent = ''; }
      else {
      let tzName = section.dataset.tzName || '';
      let tzAbbr = section.dataset.tzAbbr || '';
      const forceIanaLbl = section.dataset.tzForceIana || '';
      if (forceIanaLbl) {
        tzName = tzLongFor(forceIanaLbl) || tzName;
        tzAbbr = tzAbbrFor(forceIanaLbl) || tzAbbr;
      }
      if (!tzName && !tzAbbr && section.classList.contains('home-next-nets')) {
        const fallbackLong = tzLongFor(DEFAULT_TZ_IANA);
        const fallbackAbbr = tzAbbrFor(DEFAULT_TZ_IANA);
        tzName = fallbackLong || tzName;
        tzAbbr = fallbackAbbr || tzAbbr;
      }
      if (showAbbr) {
        if (tzName && tzAbbr) tzSpan.textContent = ` (${tzName} (${tzAbbr}))`;
        else if (tzAbbr) tzSpan.textContent = ` (${tzAbbr})`;
        else if (tzName) tzSpan.textContent = ` (${tzName})`;
        else tzSpan.textContent = ' (varies)';
      } else {
        if (tzName) tzSpan.textContent = ` (${tzName})`;
        else tzSpan.textContent = ' (varies)';
      }
      }
    }
    const myTzSpan = myBtn ? myBtn.querySelector('[data-time-my-tz-label]') : null;
    if (myTzSpan) {
      if (!showLabel) { myTzSpan.textContent = ''; }
      else {
        const long = localLong();
        const ab = localAbbr();
        if (showAbbr) {
          if (long && ab) myTzSpan.textContent = ` (${long} (${ab}))`;
          else if (ab) myTzSpan.textContent = ` (${ab})`;
          else if (long) myTzSpan.textContent = ` (${long})`;
          else myTzSpan.textContent = '';
        } else {
          myTzSpan.textContent = long ? ` (${long})` : '';
        }
      }
    }
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
  // Don't rebroadcast on initial load; hydration runs once separately
  apply(initView, { silent: true });

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
