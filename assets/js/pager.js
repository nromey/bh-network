(() => {
  function initPager(section) {
    const list = section.querySelector('[data-pager-list]');
    if (!list) return;
    const allItems = Array.from(list.children);
    let activeIdxs = allItems.map((_, i) => i); // filtered set (indices into allItems)
    const sizeSelect = section.querySelector('[data-pager-size]');
    const sizeButtons = Array.from(section.querySelectorAll('[data-pager-size-btn]'));
    const prevBtn = section.querySelector('[data-pager-prev]');
    const nextBtn = section.querySelector('[data-pager-next]');
    const firstBtn = section.querySelector('[data-pager-first]');
    const lastBtn = section.querySelector('[data-pager-last]');
    const pagesEl = section.querySelector('[data-pager-pages]');
    const statusEl = section.querySelector('[data-pager-status]');
    const statusVisible = section.querySelector('[data-pager-status-visible]');
    const helpEl = section.querySelector('.pager-help');
    const pagerNavEl = section.querySelector('.pager-nav');
    const shortcutsToggleBtn = section.querySelector('[data-pager-shortcuts-toggle]');
    const focusPref = (section.getAttribute('data-pager-focus') || 'heading').toLowerCase();
    const labelledbyId = section.getAttribute('aria-labelledby');
    const headingEl = labelledbyId ? document.getElementById(labelledbyId) : null;
    const defaultSizeAttr = section.getAttribute('data-default-size');
    const sectionId = section.id || Math.random().toString(36).slice(2);
    const storageKey = `pager:${sectionId}:size`;
    const shortcutsKey = `pager:${sectionId}:shortcuts`;
    // Per-section URL params for deep-linking state
    const pageParam = `${sectionId}-page`;
    const sizeParam = `${sectionId}-size`;
    const qParam = `${sectionId}-q`;
    const catParam = `${sectionId}-cat`; // may appear multiple times

    function parseSize(val) {
      if (!val || val === 'all') return Infinity;
      const n = parseInt(val, 10);
      return Number.isFinite(n) && n > 0 ? n : 5;
    }

    // Read URL params first, then localStorage, then select/default
    const url = new URL(window.location.href);
    const urlSize = url.searchParams.get(sizeParam);
    const urlPage = url.searchParams.get(pageParam);
    const urlQ = url.searchParams.get(qParam);
    const urlCats = url.searchParams.getAll(catParam);
    let pageSize = parseSize(urlSize || localStorage.getItem(storageKey) || (sizeSelect ? sizeSelect.value : defaultSizeAttr) || '5');
    let page = urlPage ? Math.max(1, parseInt(urlPage, 10) || 1) : 1;

    // Keyboard shortcuts enabled? Default OFF unless stored as 'on'
    let shortcutsEnabled = (localStorage.getItem(shortcutsKey) === 'on');
    function applyShortcutsState() {
      if (shortcutsToggleBtn) {
        shortcutsToggleBtn.setAttribute('aria-pressed', shortcutsEnabled ? 'true' : 'false');
        shortcutsToggleBtn.textContent = shortcutsEnabled ? 'Disable keyboard shortcuts' : 'Enable keyboard shortcuts';
      }
      if (helpEl) helpEl.hidden = !shortcutsEnabled;
      if (pagerNavEl) {
        if (shortcutsEnabled) {
          pagerNavEl.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight PageUp PageDown Home End');
        } else {
          pagerNavEl.removeAttribute('aria-keyshortcuts');
        }
      }
    }
    applyShortcutsState();

    function pageCount() {
      const total = activeIdxs.length;
      return pageSize === Infinity ? 1 : Math.max(1, Math.ceil(total / pageSize));
    }

    function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }

    let shouldFocusAfterRender = false;

    function focusAfterRender() {
      if (!shouldFocusAfterRender) return;
      shouldFocusAfterRender = false;
      switch (focusPref) {
        case 'list': {
          const listEl = section.querySelector('[data-pager-list]');
          if (listEl) {
            if (!listEl.hasAttribute('tabindex')) listEl.setAttribute('tabindex', '-1');
            listEl.focus();
          }
          break;
        }
        case 'heading': {
          if (headingEl) {
            if (!headingEl.hasAttribute('tabindex')) headingEl.setAttribute('tabindex', '-1');
            headingEl.focus();
          }
          break;
        }
        case 'none':
        default:
          break;
      }
    }

    function render() {
      const totalPages = pageCount();
      page = clamp(page, 1, totalPages);
      const totalActive = activeIdxs.length;
      const start = pageSize === Infinity ? 0 : (page - 1) * pageSize;
      const end = pageSize === Infinity ? totalActive : Math.min(totalActive, start + pageSize);
      // Hide all, then show only current page's matching items
      allItems.forEach(li => { li.hidden = true; });
      for (let i = start; i < end; i++) {
        const idx = activeIdxs[i];
        if (idx != null && allItems[idx]) allItems[idx].hidden = false;
      }
      const onFirst = page <= 1;
      const onLast = page >= totalPages;
      if (prevBtn) prevBtn.disabled = onFirst;
      if (nextBtn) nextBtn.disabled = onLast;
      if (firstBtn) firstBtn.disabled = onFirst;
      if (lastBtn) lastBtn.disabled = onLast;
      if (pagesEl) {
        // Build number buttons
        pagesEl.innerHTML = '';
        const makeBtn = (p) => {
          const b = document.createElement('button');
          b.type = 'button';
          b.textContent = String(p);
          b.setAttribute('data-pager-page', String(p));
          if (p === page) {
            b.setAttribute('aria-current', 'page');
            b.disabled = true;
          }
          b.addEventListener('click', () => {
            page = p;
            updateUrl();
            shouldFocusAfterRender = true;
            render();
          });
          return b;
        };
        const total = totalPages;
        // If many pages, show a compact range around current
        const maxButtons = 9; // current ±4 and first/last with ellipses
        const btns = [];
        const addEllipsis = () => { const s = document.createElement('span'); s.textContent = '…'; s.setAttribute('aria-hidden','true'); btns.push(s); };
        if (total <= maxButtons) {
          for (let p = 1; p <= total; p++) btns.push(makeBtn(p));
        } else {
          const first = 1, last = total;
          const startP = Math.max(first + 1, page - 3);
          const endP = Math.min(last - 1, page + 3);
          btns.push(makeBtn(first));
          if (startP > first + 1) addEllipsis();
          for (let p = startP; p <= endP; p++) btns.push(makeBtn(p));
          if (endP < last - 1) addEllipsis();
          btns.push(makeBtn(last));
        }
        btns.forEach(el => pagesEl.appendChild(el));
      }
      const visibleCount = pageSize === Infinity ? totalActive : Math.min(pageSize, Math.max(0, totalActive - start));
      if (statusEl) statusEl.textContent = `Page ${page} of ${totalPages}. Showing ${visibleCount} of ${totalActive} items.`;
      if (statusVisible) statusVisible.textContent = `Page ${page} of ${totalPages}`;
      // Sync size button pressed state
      if (sizeButtons.length) {
        sizeButtons.forEach(btn => {
          const v = btn.getAttribute('data-pager-size-btn');
          const isAll = (v === 'all' && pageSize === Infinity);
          const isNum = (parseInt(v,10) === pageSize);
          btn.setAttribute('aria-pressed', (isAll || isNum) ? 'true' : 'false');
        });
      }
      // Sync select if present
      if (sizeSelect) {
        const v = (pageSize === Infinity) ? 'all' : String(pageSize);
        if (sizeSelect.value !== v) sizeSelect.value = v;
      }
      focusAfterRender();
    }

    function updateUrl() {
      try {
        const u = new URL(window.location.href);
        // size + page
        if (pageSize === Infinity) {
          u.searchParams.set(sizeParam, 'all');
        } else {
          u.searchParams.set(sizeParam, String(pageSize));
        }
        u.searchParams.set(pageParam, String(page));
        // search query
        if (searchInput && searchInput.value && searchInput.value.trim() !== '') {
          u.searchParams.set(qParam, searchInput.value.trim());
        } else {
          u.searchParams.delete(qParam);
        }
        // categories (clear then add current)
        u.searchParams.delete(catParam);
        if (selectedCats && selectedCats.length) {
          selectedCats.forEach(c => {
            if (c && c.trim() !== '') u.searchParams.append(catParam, c.trim());
          });
        }
        history.replaceState(null, '', u.toString());
      } catch (e) { /* ignore */ }
    }

    // Optional search support
    const searchInput = section.querySelector('[data-pager-search]');
    const searchClear = section.querySelector('[data-pager-search-clear]');
    // Optional category filter support
    const catSelect = section.querySelector('[data-pager-cat-select]');
    const catAdd = section.querySelector('[data-pager-cat-add]');
    const catClear = section.querySelector('[data-pager-cat-clear]');
    const catActive = section.querySelector('[data-pager-cat-active]');
    const RESERVED = new Set(['news','cqbh']);
    let selectedCats = [];

    function parseCatsFromItem(li) {
      const raw = (li.getAttribute('data-cats') || '').trim();
      if (!raw) return [];
      return raw.split(',').map(s => s.trim()).filter(Boolean);
    }

    function listAllCats() {
      const set = new Set();
      allItems.forEach(li => {
        parseCatsFromItem(li).forEach(c => {
          const key = c.toLowerCase();
          if (!RESERVED.has(key)) set.add(c);
        });
      });
      return Array.from(set).sort((a,b)=>a.localeCompare(b));
    }

    function populateCatSelect() {
      if (!catSelect) return;
      const existing = new Set(Array.from(catSelect.options).map(o => o.value.toLowerCase()));
      listAllCats().forEach(c => {
        if (!existing.has(c.toLowerCase())) {
          const opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c;
          catSelect.appendChild(opt);
        }
      });
    }

    function updateCatChips() {
      if (!catActive) return;
      catActive.innerHTML = '';
      selectedCats.forEach(c => {
        const chip = document.createElement('span');
        chip.className = 'pager-cat-chip';
        chip.textContent = c;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.setAttribute('data-remove-cat', c);
        btn.setAttribute('aria-label', `Remove category ${c}`);
        btn.textContent = '×';
        btn.addEventListener('click', () => {
          selectedCats = selectedCats.filter(x => x.toLowerCase() !== c.toLowerCase());
          buildActive();
        });
        chip.appendChild(btn);
        catActive.appendChild(chip);
      });
    }

    function buildActive() {
      const q = (searchInput && searchInput.value || '').toLowerCase().trim();
      const needCats = selectedCats.map(c => c.toLowerCase());
      activeIdxs = [];
      for (let i = 0; i < allItems.length; i++) {
        const li = allItems[i];
        // text match
        const txt = li.textContent || '';
        const okText = !q || txt.toLowerCase().indexOf(q) !== -1;
        if (!okText) continue;
        // category match: require all selected
        const cats = parseCatsFromItem(li).map(c => c.toLowerCase());
        let okCats = true;
        for (const c of needCats) { if (!cats.includes(c)) { okCats = false; break; } }
        if (!okCats) continue;
        activeIdxs.push(i);
      }
      page = 1;
      if (statusEl) statusEl.textContent = `Filtered to ${activeIdxs.length} of ${allItems.length} items.`;
      populateCatSelect();
      updateCatChips();
      render();
    }

    if (searchInput) {
      let t;
      // Initialize from URL param
      if (urlQ) {
        searchInput.value = urlQ;
      }
      searchInput.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(() => { buildActive(); updateUrl(); }, 200);
      });
      if (searchClear) {
        searchClear.addEventListener('click', () => {
          searchInput.value = '';
          buildActive();
          updateUrl();
          searchInput.focus();
        });
      }
    }

    if (catSelect && catAdd) {
      populateCatSelect();
      catAdd.addEventListener('click', () => {
        const v = catSelect.value.trim();
        if (!v) return;
        if (!selectedCats.some(x => x.toLowerCase() === v.toLowerCase())) {
          selectedCats.push(v);
          buildActive();
          updateUrl();
        }
      });
    }
    if (catClear) {
      catClear.addEventListener('click', () => {
        selectedCats = [];
        buildActive();
        updateUrl();
        if (catSelect) catSelect.focus();
      });
    }

    // Initialize categories from URL params (if any), then build
    if (urlCats && urlCats.length) {
      // Avoid reserved and duplicates (case-insensitive)
      const seen = new Set();
      urlCats.forEach(c => {
        const cc = (c || '').trim();
        if (!cc) return;
        const low = cc.toLowerCase();
        if (RESERVED.has(low)) return;
        if (!seen.has(low)) { selectedCats.push(cc); seen.add(low); }
      });
    }
    buildActive();

    if (sizeSelect) {
      // Initialize select to stored value if present
      const stored = localStorage.getItem(storageKey);
      if (stored && stored !== 'Infinity') {
        const opt = Array.from(sizeSelect.options).find(o => o.value === stored);
        if (opt) sizeSelect.value = stored;
      } else if (stored === 'Infinity') {
        sizeSelect.value = 'all';
      }
      sizeSelect.addEventListener('change', () => {
        const v = sizeSelect.value;
        pageSize = parseSize(v);
        localStorage.setItem(storageKey, v === 'all' ? 'Infinity' : v);
        page = 1;
        updateUrl();
        shouldFocusAfterRender = true;
        render();
      });
    }

    if (sizeButtons.length) {
      sizeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          const v = btn.getAttribute('data-pager-size-btn') || '5';
          pageSize = parseSize(v);
          localStorage.setItem(storageKey, v === 'all' ? 'Infinity' : v);
          page = 1;
          updateUrl();
          shouldFocusAfterRender = true;
          render();
        });
      });
    }

    if (firstBtn) firstBtn.addEventListener('click', () => { page = 1; updateUrl(); shouldFocusAfterRender = true; render(); });
    if (prevBtn) prevBtn.addEventListener('click', () => { page -= 1; updateUrl(); shouldFocusAfterRender = true; render(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { page += 1; updateUrl(); shouldFocusAfterRender = true; render(); });
    if (lastBtn) lastBtn.addEventListener('click', () => { page = pageCount(); updateUrl(); shouldFocusAfterRender = true; render(); });

    // Keyboard shortcuts when focus is within this section
    section.addEventListener('keydown', (ev) => {
      if (!shortcutsEnabled) return;
      const t = ev.target;
      const tag = (t.tagName || '').toLowerCase();
      // Avoid intercepting keys while focus is on form controls or pager buttons
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable) return;
      if (t.closest && t.closest('.pager-toolbar, .pager-nav')) return;
      const total = pageCount();
      let handled = false;
      switch (ev.key) {
        case 'ArrowLeft':
        case 'PageUp':
          if (page > 1) { page -= 1; handled = true; }
          break;
        case 'ArrowRight':
        case 'PageDown':
          if (page < total) { page += 1; handled = true; }
          break;
        case 'Home':
          if (page !== 1) { page = 1; handled = true; }
          break;
        case 'End':
          if (page !== total) { page = total; handled = true; }
          break;
      }
      if (handled) {
        ev.preventDefault();
        updateUrl();
        shouldFocusAfterRender = true;
        render();
      }
    });

    if (shortcutsToggleBtn) {
      shortcutsToggleBtn.addEventListener('click', () => {
        shortcutsEnabled = !shortcutsEnabled;
        localStorage.setItem(shortcutsKey, shortcutsEnabled ? 'on' : 'off');
        applyShortcutsState();
        if (statusEl) {
          statusEl.textContent = shortcutsEnabled ? 'Keyboard shortcuts enabled.' : 'Keyboard shortcuts disabled.';
        }
      });
    }

    // Initial render
    render();
  }

  function initAll() {
    const sections = document.querySelectorAll('[data-pager]');
    sections.forEach(initPager);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
