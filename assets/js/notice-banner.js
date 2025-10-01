// /assets/js/notice-banner.js
(function () {
  const KEY = (id) => `notice:${id}:dismissed`;

  const enhanceTables = (container) => {
    container.querySelectorAll('.notice-content table').forEach((table) => {
      const captionText = table.getAttribute('data-caption');
      const hasCaption = table.querySelector(':scope > caption');
      if (captionText && !hasCaption) {
        const cap = document.createElement('caption');
        cap.textContent = captionText;
        table.insertBefore(cap, table.firstChild);
      }
      if (!table.hasAttribute('role')) table.setAttribute('role', 'table');
      if (!table.hasAttribute('aria-label') && captionText) {
        table.setAttribute('aria-label', captionText);
      }
      table.classList.add('connect-table');
      const thead = table.tHead;
      if (thead) {
        thead.querySelectorAll('th').forEach((th) => {
          if (!th.hasAttribute('scope')) th.setAttribute('scope', 'col');
        });
      }
    });
  };

  const init = () => {
    document.querySelectorAll('.notice-banner[data-notice-id]').forEach((el) => {
      const id = el.getAttribute('data-notice-id');
      if (!id) return;
      let dismissed = false;
      try { dismissed = localStorage.getItem(KEY(id)) === '1'; } catch (_) {}
      if (!dismissed) {
        el.removeAttribute('hidden');
      }
      enhanceTables(el);
    });
  };

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-notice-dismiss]');
    if (!btn) return;
    const container = btn.closest('.notice-banner[data-notice-id]');
    if (!container) return;
    const id = container.getAttribute('data-notice-id');
    try { localStorage.setItem(KEY(id), '1'); } catch (_) {}
    container.setAttribute('hidden', 'hidden');
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

