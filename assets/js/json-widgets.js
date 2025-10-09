// assets/js/json-widgets.js
// Progressive enhancement: fetch remote JSON for Next Net card and NCO schedule.
// If fetch fails, the server-rendered Liquid output remains visible.

(function () {
  const cache = new Map();

  async function fetchJSON(url) {
    try {
      if (cache.has(url)) return cache.get(url);
      const resp = await fetch(url, { credentials: 'omit', mode: 'cors', cache: 'no-store' });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      cache.set(url, data);
      return data;
    } catch (e) {
      // Quiet failure: leave existing content in place
      console.warn('[bhn] JSON fetch failed for', url, e);
      return null;
    }
  }

  function tzDisplay(tz) {
    if (!tz) return '';
    switch (tz) {
      case 'America/New_York': return 'Eastern';
      case 'America/Chicago': return 'Central';
      case 'America/Denver': return 'Mountain';
      case 'America/Los_Angeles': return 'Pacific';
      default: return tz;
    }
  }

  function normalizeCategory(raw) {
    const s = String(raw || '').trim().toLowerCase();
    if (!s) return '';
    // Common normalizations
    if (s === 'bhn' || s === 'blind hams' || s === 'blind-hams' || s === 'blind hams network' || s === 'blind-hams-network') return 'bhn';
    if (s === 'disability' || s === 'disabilities') return 'disability';
    if (s === 'general' || s === 'general interest' || s === 'gen') return 'general';
    return s; // pass through for any future categories
  }

  function formatDateAt(iso) {
    try {
      const d = new Date(iso);
      const date = d.toLocaleDateString(undefined, {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
      });
      const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
      return `${date} at ${time}`;
    } catch (_) { return iso; }
  }

  function detectUpdatedAt(obj) {
    if (!obj || typeof obj !== 'object') return null;
    const keys = ['updated_at', 'generated_at', 'timestamp', 'updated', 'last_updated', 'lastModified'];
    for (const k of keys) {
      if (obj[k]) return obj[k];
    }
    return null;
  }

  function appendUpdatedAt(container, data) {
    if (!container || !data) return;
    const ts = detectUpdatedAt(data);
    if (!ts) return;
    let when;
    try {
      const d = new Date(ts);
      when = d.toLocaleString();
    } catch (_) {
      when = String(ts);
    }
    const prev = container.querySelector('.data-updated');
    if (prev) prev.remove();
    const p = document.createElement('p');
    p.className = 'data-updated';
    p.setAttribute('aria-live', 'polite');
    p.textContent = `Data updated ${when}`;
    container.appendChild(p);
  }

  function enhanceNextNet() {
    const sections = document.querySelectorAll('[data-next-net-json]');
    if (!sections.length) return;
    sections.forEach(async (section) => {
      const url = section.getAttribute('data-next-net-json');
      if (!url) return;
      const data = await fetchJSON(url);
      if (!data) return;

      // Determine the best "next" occurrence: always prefer earliest upcoming BHN.
      // If no BHN entries exist in the future window, fall back to earliest of any category.
      const now = new Date();
      const week = Array.isArray(data.week) ? data.week.slice() : [];
      const containerWeek = section.querySelector('#home-week-nets');
      const primaryCat = 'bhn'; // Force BHN as the "Next Net" category

      function isFuture(iso) {
        try { return new Date(iso) > now; } catch (_) { return false; }
      }

      // Build future pools
      const futureWeek = week.filter((o) => o && o.start_local_iso && isFuture(o.start_local_iso));
      const futureNext = (data.next_net && data.next_net.start_local_iso && isFuture(data.next_net.start_local_iso)) ? [data.next_net] : [];

      function earliest(arr) {
        return arr
          .filter((o) => o && o.start_local_iso)
          .sort((a, b) => new Date(a.start_local_iso) - new Date(b.start_local_iso))[0] || null;
      }

      let next = null;
      const isCat = (o, cat) => (normalizeCategory(o && o.category) === normalizeCategory(cat));
      const primaryPool = futureWeek.filter((o) => isCat(o, primaryCat))
        .concat(futureNext.filter((o) => isCat(o, primaryCat)));
      next = earliest(primaryPool);
      if (!next) next = earliest(futureWeek.concat(futureNext));
      if (!next) return;

      const card = section.querySelector('.next-net-card');
      if (!card) return;

      const title = card.querySelector('h3');
      if (title) title.textContent = next.name || '';

      const timeEl = card.querySelector('time');
      if (timeEl) {
        timeEl.setAttribute('datetime', next.start_local_iso || '');
        timeEl.textContent = formatDateAt(next.start_local_iso || '');
      }

      const tzEl = card.querySelector('.next-net-tz');
      if (tzEl) tzEl.textContent = tzDisplay(next.time_zone || '');

      const dur = card.querySelector('.next-net-duration');
      if (next.duration_min) {
        if (dur) dur.textContent = `· ${next.duration_min} min`;
        else {
          const span = document.createElement('span');
          span.className = 'next-net-duration';
          span.textContent = `· ${next.duration_min} min`;
          const meta = card.querySelector('.next-net-meta');
          if (meta) meta.appendChild(document.createTextNode(' '));
          if (meta) meta.appendChild(span);
        }
      } else if (dur) {
        dur.remove();
      }

      const desc = card.querySelector('.next-net-description') || card.querySelector('h4 ~ p');
      if (desc) desc.textContent = next.description || '';

      // Connections block (if present)
      const pConn = card.querySelector('.next-net-connections');
      if (pConn && next.connections) {
        const allstar = (next.connections.allstar || '').trim() || '—';
        const echolink = (next.connections.echolink || '').trim() || '—';
        const other = buildOtherModes(next);
        pConn.innerHTML = '';
        const lab = document.createElement('span');
        lab.className = 'next-net-label';
        lab.textContent = 'Connections';
        pConn.appendChild(lab);
        pConn.appendChild(document.createTextNode(` AllStar: ${allstar}, `));
        pConn.appendChild(document.createTextNode(`EchoLink: ${echolink}`));
        if (other) pConn.appendChild(document.createTextNode(`, Other: ${other}`));
      }

      appendUpdatedAt(section, data);
    });
  }

  function enhanceNcoTable() {
    const containers = document.querySelectorAll('[data-nco-json]');
    if (!containers.length) return;
    containers.forEach(async (wrap) => {
      const url = wrap.getAttribute('data-nco-json');
      if (!url) return;
      const data = await fetchJSON(url);
      if (!data) return;

      const table = wrap.querySelector('table.nco-table');
      if (!table) return;

      const tbody = table.querySelector('tbody');
      if (!tbody) return;

      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) return;

      const timeLocal = data.time_local || null; // e.g., "10:00"
      const tzFull = data.tz_full || null;      // e.g., "Eastern"

      // Update Time (TZ) column header if provided
      if (tzFull) {
        try {
          const ths = table.querySelectorAll('thead th');
          // The 4th column is Time (index 3) when show_location is true
          if (ths && ths.length >= 4) {
            ths[3].textContent = `Time (${tzFull})`;
          }
        } catch (_) {}
      }

      const rows = document.createDocumentFragment();
      items.forEach((r, idx) => {
        const dateIso = r.date || '';
        const dateDisp = dateIso ? new Date(dateIso + 'T00:00:00').toLocaleDateString(undefined, {
          weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
        }) : '';
        const nco = (r.nco || r.operator || '').trim();
        const notes = r.notes || '';
        const unassigned = !!(r.unassigned || !nco || nco.toUpperCase() === 'TBD');

        const tr = document.createElement('tr');
        if (unassigned) tr.classList.add('nco-unassigned');

        const thDate = document.createElement('th');
        thDate.setAttribute('scope', 'row');
        thDate.setAttribute('data-title', 'Date');
        const t = document.createElement('time');
        if (dateIso) t.setAttribute('datetime', dateIso);
        t.textContent = dateDisp || dateIso;
        thDate.appendChild(t);
        tr.appendChild(thDate);

        const tdNco = document.createElement('td');
        tdNco.setAttribute('data-title', 'NCO');
        tdNco.textContent = nco || 'TBD';
        if (unassigned) {
          const span = document.createElement('span');
          span.className = 'sr-only';
          span.id = `unassigned-${idx}`;
          span.textContent = ' — Unassigned';
          tdNco.setAttribute('aria-describedby', span.id);
          tdNco.appendChild(span);
        }
        tr.appendChild(tdNco);

        // Optional Location column may be present; if so, preserve table structure by inserting an empty cell
        const theadCells = table.querySelectorAll('thead th');
        const hasLocation = theadCells && theadCells.length >= 5; // Date, NCO, Location, Time, Notes
        if (hasLocation) {
          const tdLoc = document.createElement('td');
          tdLoc.setAttribute('data-title', 'Location');
          tdLoc.textContent = data.location_md ? '' : 'Blind Hams Bridge';
          tr.appendChild(tdLoc);
        }

        const tdTime = document.createElement('td');
        tdTime.setAttribute('data-title', 'Time');
        tdTime.textContent = timeLocal ? new Date(`2000-01-01T${timeLocal}:00`).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) + (tzFull ? ` ${tzFull}` : '') : '—';
        tr.appendChild(tdTime);

        const tdNotes = document.createElement('td');
        tdNotes.setAttribute('data-title', 'Notes');
        tdNotes.textContent = notes;
        tr.appendChild(tdNotes);

        rows.appendChild(tr);
      });

      // Replace tbody content
      tbody.innerHTML = '';
      tbody.appendChild(rows);

      appendUpdatedAt(wrap, data);
    });
  }

  function fmtWeekWhen(iso) {
    try {
      const d = new Date(iso);
      const day = d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
      const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
      return `${day} at ${time}`;
    } catch (_) { return iso; }
  }

  function getConn(occ, key) {
    try { return occ && occ.connections && occ.connections[key]; } catch (_) { return null; }
  }

  function buildOtherModes(occ) {
    const out = [];
    const freq = getConn(occ, 'frequency');
    const mode = getConn(occ, 'mode');
    if (freq) out.push(mode ? `${freq} ${mode}` : `${freq}`);
    const dmr_sys = getConn(occ, 'dmr_system');
    const dmr_tg = getConn(occ, 'dmr_tg');
    const dmr = getConn(occ, 'dmr');
    if (dmr_sys && dmr_tg) out.push(`DMR ${dmr_sys} TG ${dmr_tg}`);
    else if (dmr) out.push(`DMR ${dmr}`);
    else if ((mode || '').toString().toUpperCase() === 'DMR') out.push('DMR');
    const tg = getConn(occ, 'talkgroup');
    if (tg && !(dmr_sys && dmr_tg)) out.push(`Talkgroup ${tg}`);
    const dstar = getConn(occ, 'dstar'); if (dstar) out.push(`D-STAR ${dstar}`);
    const peanut = getConn(occ, 'peanut'); if (peanut) out.push(`Peanut ${peanut}`);
    const ysf = getConn(occ, 'ysf'); if (ysf) out.push(`YSF ${ysf}`);
    const wiresx = getConn(occ, 'wiresx') || getConn(occ, 'wires_x'); if (wiresx) out.push(`WIRES-X ${wiresx}`);
    const p25 = getConn(occ, 'p25'); if (p25) out.push(`P25 ${p25}`);
    const nxdn = getConn(occ, 'nxdn'); if (nxdn) out.push(`NXDN ${nxdn}`);
    return out.join(', ');
  }

  function enhanceWeekList() {
    const sections = document.querySelectorAll('[data-next-net-json]');
    if (!sections.length) return;
    sections.forEach(async (container) => {
      const url = container.getAttribute('data-next-net-json');
      if (!url) return;
      const data = await fetchJSON(url);
      if (!data || !Array.isArray(data.week)) return;

      const now = new Date();
      const week = data.week
        .filter((o) => {
          try { return new Date(o.start_local_iso) >= now; } catch (_) { return true; }
        })
        .sort((a, b) => new Date(a.start_local_iso) - new Date(b.start_local_iso));
      const weekBlock = container.querySelector('#home-week-nets');
      if (!weekBlock) return;

      const tbody = weekBlock.querySelector('.view-table tbody');
      const headingsView = weekBlock.querySelector('.view-headings');
      if (!tbody || !headingsView) return;

      const primary = weekBlock.dataset.primaryCategory || (data.primary_category || '');

      // Build table rows
      const tfrag = document.createDocumentFragment();
      week.forEach((occ) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-category-item', '');
        tr.dataset.category = normalizeCategory(occ.category || '');

        // Net
        const tdNet = document.createElement('td');
        const strong = document.createElement('strong');
        strong.textContent = occ.name || '';
        tdNet.appendChild(strong);
        tr.appendChild(tdNet);

        // Description
        const tdDesc = document.createElement('td');
        tdDesc.className = 'net-desc';
        tdDesc.textContent = occ.description || '';
        tr.appendChild(tdDesc);

        // When
        const tdWhen = document.createElement('td');
        const time = document.createElement('time');
        if (occ.start_local_iso) time.setAttribute('datetime', occ.start_local_iso);
        time.textContent = fmtWeekWhen(occ.start_local_iso || '');
        const tzSpan = document.createElement('span');
        tzSpan.className = 'next-net-tz';
        tzSpan.textContent = tzDisplay(occ.time_zone || '');
        tdWhen.appendChild(time);
        tdWhen.appendChild(document.createTextNode(' '));
        tdWhen.appendChild(tzSpan);
        tr.appendChild(tdWhen);

        // Duration
        const tdDur = document.createElement('td');
        tdDur.textContent = occ.duration_min ? `${occ.duration_min} min` : '—';
        tr.appendChild(tdDur);

        // AllStar / EchoLink
        const tdAllStar = document.createElement('td');
        tdAllStar.textContent = getConn(occ, 'allstar') || '—';
        tr.appendChild(tdAllStar);
        const tdEcho = document.createElement('td');
        tdEcho.textContent = getConn(occ, 'echolink') || '—';
        tr.appendChild(tdEcho);

        // Other modes
        const tdOther = document.createElement('td');
        const other = buildOtherModes(occ);
        tdOther.textContent = other || '—';
        tr.appendChild(tdOther);

        tfrag.appendChild(tr);
      });

      // Build headings view items
      const hfrag = document.createDocumentFragment();
      week.forEach((occ, idx) => {
        const art = document.createElement('article');
        art.className = 'next-net-item';
        art.setAttribute('aria-labelledby', `week-net-${idx+1}`);
        art.setAttribute('data-category-item', '');
        art.dataset.category = normalizeCategory(occ.category || '');

        const h4 = document.createElement('h4');
        h4.id = `week-net-${idx+1}`;
        h4.textContent = occ.name || '';
        art.appendChild(h4);

        const pMeta = document.createElement('p');
        pMeta.className = 'next-net-meta';
        const label = document.createElement('span');
        label.className = 'next-net-label';
        label.textContent = 'When';
        pMeta.appendChild(label);
        const time = document.createElement('time');
        if (occ.start_local_iso) time.setAttribute('datetime', occ.start_local_iso);
        time.textContent = fmtWeekWhen(occ.start_local_iso || '');
        pMeta.appendChild(document.createTextNode(' '));
        pMeta.appendChild(time);
        const tz = document.createElement('span');
        tz.className = 'next-net-tz';
        tz.textContent = tzDisplay(occ.time_zone || '');
        pMeta.appendChild(document.createTextNode(' '));
        pMeta.appendChild(tz);
        if (occ.duration_min) {
          const spanDur = document.createElement('span');
          spanDur.className = 'next-net-duration';
          spanDur.textContent = `· ${occ.duration_min} min`;
          pMeta.appendChild(document.createTextNode(' '));
          pMeta.appendChild(spanDur);
        }
        art.appendChild(pMeta);

        const pConn = document.createElement('p');
        pConn.className = 'next-net-connections';
        const lab2 = document.createElement('span');
        lab2.className = 'next-net-label';
        lab2.textContent = 'Connections';
        pConn.appendChild(lab2);
        const allstar = getConn(occ, 'allstar') || '—';
        const echolink = getConn(occ, 'echolink') || '—';
        const other = buildOtherModes(occ);
        pConn.appendChild(document.createTextNode(` AllStar: ${allstar}, EchoLink: ${echolink}`));
        if (other) pConn.appendChild(document.createTextNode(`, Other: ${other}`));
        art.appendChild(pConn);

        const h5About = document.createElement('h5');
        h5About.textContent = 'About this net';
        art.appendChild(h5About);
        const desc = document.createElement('div');
        desc.className = 'week-net-description';
        desc.textContent = occ.description || '';
        art.appendChild(desc);

        const h5Where = document.createElement('h5');
        h5Where.textContent = 'Where';
        art.appendChild(h5Where);
        const pWhere = document.createElement('p');
        pWhere.textContent = 'Blind Hams Bridge';
        art.appendChild(pWhere);

        hfrag.appendChild(art);
      });

      // Replace contents
      tbody.innerHTML = '';
      tbody.appendChild(tfrag);
      // Clear items inside headings view container div
      // The first child elements are articles; keep container itself
      headingsView.innerHTML = '';
      headingsView.appendChild(hfrag);

      appendUpdatedAt(container, data);
    });
  }

  function init() {
    enhanceNextNet();
    enhanceWeekList();
    enhanceNcoTable();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
