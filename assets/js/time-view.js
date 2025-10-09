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
    status.textContent = view === 'my' ? 'Showing times in your timezone.' : 'Showing times in net timezone.';
  }
  function apply(view) {
    document.querySelectorAll('.home-next-nets, .nets-section').forEach((section) => {
      const btns = section.querySelectorAll('[data-time-button]');
      btns.forEach((b) => b.setAttribute('aria-pressed', b.dataset.timeButton === view ? 'true' : 'false'));
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
})();

