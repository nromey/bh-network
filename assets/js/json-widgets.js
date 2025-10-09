// assets/js/json-widgets.js
// Progressive enhancement: fetch remote JSON for Next Net card and NCO schedule.
// If fetch fails, the server-rendered Liquid output remains visible.

(function () {
  const cache = new Map();
  const DIAG = (() => {
    try { return new URLSearchParams(location.search).get('diag') === '1'; }
    catch (_) { return false; }
  })();

  // Global time view: 'net' (event-local) or 'my' (viewer-local)
  let TIME_VIEW = 'net';
  let SHOW_UTC = false;
  try {
    const v = localStorage.getItem('timeView:global');
    if (v === 'my') TIME_VIEW = 'my';
    SHOW_UTC = localStorage.getItem('timeView:showUTC') === '1';
  } catch (_) {}

  function appendDiag(container, text, live = 'polite') {
    try {
      if (!container || !text) return;
      const p = document.createElement('p');
      p.className = 'data-diag';
      p.setAttribute('role', 'status');
      p.setAttribute('aria-live', live);
      p.textContent = String(text);
      container.appendChild(p);
    } catch (_) { /* ignore */ }
  }

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

  function tzAbbr(iana, isoLike) {
    try {
      if (!iana) return '';
      const d = isoLike ? new Date(isoLike) : new Date();
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'short' }).formatToParts(d);
      const part = parts.find(p => p.type === 'timeZoneName');
      if (!part) return '';
      // Typically returns 'EST', 'EDT', 'CST', etc. For some zones may be 'GMT-5'.
      // Normalize 'GMT' forms to uppercase as-is.
      return String(part.value).toUpperCase();
    } catch (_) { return ''; }
  }

  function tzFromISO(iso) {
    try {
      const d = new Date(iso);
      const mins = -d.getTimezoneOffset(); // local offset, but cannot infer source zone
      // Fallback: derive from ISO string offset when present
      const m = String(iso || '').match(/([+-])(\d{2}):(\d{2})$/);
      if (m) {
        const sign = m[1] === '-' ? -1 : 1;
        const off = sign * (parseInt(m[2], 10) * 60 + parseInt(m[3], 10));
        switch (off) {
          case -300: case -240: return 'Eastern';
          case -360: case -300: return 'Central';
          case -420: case -360: return 'Mountain';
          case -480: case -420: return 'Pacific';
          default: return `UTC${m[1]}${m[2]}:${m[3]}`;
        }
      }
    } catch (_) {}
    return '';
  }

  function fmtUTC(iso) {
    try {
      const d = new Date(iso);
      const t = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' });
      return `UTC ${t}`;
    } catch (_) { return ''; }
  }

  function getStartISO(obj) {
    return (obj && (obj.start_local_iso || obj.start_iso)) || '';
  }

  function getEndISO(obj) {
    const end = (obj && (obj.end_local_iso || obj.end_iso)) || '';
    if (end) return end;
    const start = getStartISO(obj);
    const dur = (obj && obj.duration_min) ? parseInt(obj.duration_min, 10) : NaN;
    if (!start || !Number.isFinite(dur)) return '';
    try {
      const d = new Date(start);
      d.setMinutes(d.getMinutes() + dur);
      return d.toISOString();
    } catch (_) { return ''; }
  }

  function isInProgress(obj, now = new Date()) {
    try {
      const s = new Date(getStartISO(obj));
      const eiso = getEndISO(obj);
      const e = eiso ? new Date(eiso) : new Date(s.getTime() + 60*60000);
      return now >= s && now < e;
    } catch (_) { return false; }
  }

  function getWeekArray(data) {
    if (!data || typeof data !== 'object') return [];
    if (Array.isArray(data.week)) return data.week;
    if (Array.isArray(data.items)) return data.items;
    return [];
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

  // Format using the date/time written in the ISO string (no zone conversion)
  function formatISOAsWritten(iso) {
    try {
      const m = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
      if (!m) return iso || '';
      const y = parseInt(m[1], 10), mo = parseInt(m[2], 10), d = parseInt(m[3], 10);
      const h = parseInt(m[4], 10), mi = parseInt(m[5], 10);
      const dd = new Date(y, mo - 1, d);
      const weekday = dd.toLocaleDateString(undefined, { weekday: 'long' });
      const month = dd.toLocaleDateString(undefined, { month: 'long' });
      const ampm = (h % 12 || 12) + ':' + String(mi).padStart(2, '0') + ' ' + (h >= 12 ? 'PM' : 'AM');
      return `${weekday}, ${month} ${d}, ${y} at ${ampm}`;
    } catch (_) { return iso || ''; }
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
    let label = '';
    if (ts) {
      try { label = `Data updated ${new Date(ts).toLocaleString()}`; }
      catch (_) { label = `Data updated ${String(ts)}`; }
    } else {
      label = 'Live data loaded';
    }
    const prev = container.querySelector('.data-updated');
    if (prev) prev.remove();
    const p = document.createElement('p');
    p.className = 'data-updated';
    p.setAttribute('aria-live', 'polite');
    p.textContent = label;
    container.appendChild(p);
  }

  function enhanceNextNet() {
    const sections = document.querySelectorAll('[data-next-net-json]');
    if (!sections.length) return;
    sections.forEach(async (section) => {
      const url = section.getAttribute('data-next-net-json');
      if (!url) return;
      const data = await fetchJSON(url);
      if (!data) {
        if (DIAG) appendDiag(section, 'Live data fetch failed for Next Net.');
        return;
      }

      // Determine the best "next" occurrence: always prefer earliest upcoming BHN.
      // If no BHN entries exist in the future window, fall back to earliest of any category.
      const now = new Date();
      const week = getWeekArray(data).slice();
      const containerWeek = section.querySelector('#home-week-nets');
      const primaryCat = 'bhn'; // Force BHN as the "Next Net" category

      function isFuture(iso) {
        try { return new Date(iso) > now; } catch (_) { return false; }
      }

      // Build future pools
      const futureWeek = week.filter((o) => o && getStartISO(o) && isFuture(getStartISO(o)));
      const futureNext = (data.next_net && getStartISO(data.next_net) && isFuture(getStartISO(data.next_net))) ? [data.next_net] : [];

      function earliest(arr) {
        return arr
          .filter((o) => o && getStartISO(o))
          .sort((a, b) => new Date(getStartISO(a)) - new Date(getStartISO(b)))[0] || null;
      }

      let next = null;
      const isCat = (o, cat) => (normalizeCategory(o && o.category) === normalizeCategory(cat));
      const primaryPool = futureWeek.filter((o) => isCat(o, primaryCat))
        .concat(futureNext.filter((o) => isCat(o, primaryCat)));
      next = earliest(primaryPool);
      if (!next) next = earliest(futureWeek.concat(futureNext));
      if (!next) {
        if (DIAG) appendDiag(section, 'Live data loaded but no upcoming Next Net found.');
        return;
      }

      const card = section.querySelector('.next-net-card');
      if (!card) return;

      const title = card.querySelector('h3');
      if (title) title.textContent = next.name || '';

      const timeEl = card.querySelector('time');
      if (timeEl) {
        const start = getStartISO(next);
        timeEl.setAttribute('datetime', start || '');
        timeEl.textContent = (TIME_VIEW === 'my') ? formatDateAt(start || '') : formatISOAsWritten(start || '');
      }

      const tzEl = card.querySelector('.next-net-tz');
      if (tzEl) tzEl.textContent = (TIME_VIEW === 'my') ? 'Local' : (tzDisplay(next.time_zone || '') || tzFromISO(getStartISO(next)));

      // Append UTC display when enabled
      try {
        const meta = card.querySelector('.next-net-meta');
        let utcSpan = card.querySelector('.next-net-utc');
        if (SHOW_UTC) {
          if (!utcSpan) {
            utcSpan = document.createElement('span');
            utcSpan.className = 'next-net-utc';
            if (meta) meta.appendChild(document.createTextNode(' '));
            if (meta) meta.appendChild(utcSpan);
          }
          utcSpan.textContent = `· ${fmtUTC(getStartISO(next))}`;
        } else if (utcSpan) {
          utcSpan.remove();
        }
      } catch (_) {}

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
      if (DIAG) appendDiag(section, `Live data loaded. Picked Next Net: ${next.name || ''} (${next.category || ''}) at ${next.start_local_iso || ''}.`);

      // Expose tz context for this section (for toggle labeling)
      const tzIana = next.time_zone || '';
      const tzName = tzDisplay(tzIana) || '';
      const abbr = tzAbbr(tzIana, getStartISO(next));
      if (tzName) section.dataset.tzName = tzName;
      if (abbr) section.dataset.tzAbbr = abbr;
      document.dispatchEvent(new CustomEvent('bhn:tzcontext-change'));
    });
  }

  function enhanceNcoTable() {
    const containers = document.querySelectorAll('[data-nco-json]');
    if (!containers.length) return;
    containers.forEach(async (wrap) => {
      const url = wrap.getAttribute('data-nco-json');
      if (!url) return;
      const data = await fetchJSON(url);
      if (!data) {
        if (DIAG) appendDiag(wrap, 'Live data fetch failed for NCO schedule.');
        return;
      }

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
      if (DIAG) appendDiag(wrap, `Live data loaded. NCO items: ${items.length}.`);
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
      if (!data) {
        if (DIAG) appendDiag(container, 'Live data fetch failed for weekly list.');
        return;
      }
      const arr = getWeekArray(data);
      if (!Array.isArray(arr)) {
        if (DIAG) appendDiag(container, 'Live data loaded but no weekly array found.');
        return;
      }

      const now = new Date();
      const week = arr
        .filter((o) => {
          try { return new Date(getStartISO(o)) >= now; } catch (_) { return true; }
        })
        .sort((a, b) => new Date(getStartISO(a)) - new Date(getStartISO(b)));
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
        if (isInProgress(occ)) {
          tdNet.appendChild(document.createTextNode(' '));
          const vis = document.createElement('span');
          vis.className = 'next-net-live';
          vis.textContent = '(Live now!)';
          tdNet.appendChild(vis);
        }
        tr.appendChild(tdNet);

        // Description
        const tdDesc = document.createElement('td');
        tdDesc.className = 'net-desc';
        tdDesc.textContent = occ.description || '';
        tr.appendChild(tdDesc);

        // When
        const tdWhen = document.createElement('td');
        const time = document.createElement('time');
        const start = getStartISO(occ);
        if (start) time.setAttribute('datetime', start);
        time.textContent = (TIME_VIEW === 'my') ? fmtWeekWhen(start || '') : formatISOAsWritten(start || '');
        const tzSpan = document.createElement('span');
        tzSpan.className = 'next-net-tz';
        tzSpan.textContent = (TIME_VIEW === 'my') ? 'Local' : (tzDisplay(occ.time_zone || '') || tzFromISO(getStartISO(occ)));
        tdWhen.appendChild(time);
        tdWhen.appendChild(document.createTextNode(' '));
        tdWhen.appendChild(tzSpan);
        if (SHOW_UTC) {
          const utc = document.createElement('span');
          utc.className = 'next-net-utc';
          utc.textContent = ` · ${fmtUTC(start)}`;
          tdWhen.appendChild(utc);
        }
        if (isInProgress(occ)) {
          const live = document.createElement('span');
          live.className = 'next-net-live';
          live.textContent = '· Live now';
          tdWhen.appendChild(document.createTextNode(' '));
          tdWhen.appendChild(live);
        }
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
        const start2 = getStartISO(occ);
        if (start2) time.setAttribute('datetime', start2);
        time.textContent = (TIME_VIEW === 'my') ? fmtWeekWhen(start2 || '') : formatISOAsWritten(start2 || '');
        pMeta.appendChild(document.createTextNode(' '));
        pMeta.appendChild(time);
        const tz = document.createElement('span');
        tz.className = 'next-net-tz';
        tz.textContent = (TIME_VIEW === 'my') ? 'Local' : (tzDisplay(occ.time_zone || '') || tzFromISO(getStartISO(occ)));
        pMeta.appendChild(document.createTextNode(' '));
        pMeta.appendChild(tz);
        if (SHOW_UTC) {
          const utc = document.createElement('span');
          utc.className = 'next-net-utc';
          utc.textContent = ` · ${fmtUTC(start2)}`;
          pMeta.appendChild(utc);
        }
        if (occ.duration_min) {
          const spanDur = document.createElement('span');
          spanDur.className = 'next-net-duration';
          spanDur.textContent = `· ${occ.duration_min} min`;
          pMeta.appendChild(document.createTextNode(' '));
          pMeta.appendChild(spanDur);
        }
        if (isInProgress(occ)) {
          const live = document.createElement('span');
          live.className = 'next-net-live';
          live.textContent = '· Live now';
          pMeta.appendChild(document.createTextNode(' '));
          pMeta.appendChild(live);
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
      if (DIAG) appendDiag(container, `Live data loaded. Weekly items: ${week.length}.`);

      // Determine a representative tz for this container (if unified)
      try {
        const uniq = new Set();
        let sample = null;
        week.forEach((o) => {
          const tz = (o && o.time_zone) || '';
          if (tz) {
            uniq.add(tz);
            if (!sample) sample = o;
          }
        });
        if (uniq.size === 1 && sample) {
          const tzIana = sample.time_zone;
          const tzName = tzDisplay(tzIana) || '';
          const abbr = tzAbbr(tzIana, getStartISO(sample));
          if (tzName) container.dataset.tzName = tzName;
          if (abbr) container.dataset.tzAbbr = abbr;
          document.dispatchEvent(new CustomEvent('bhn:tzcontext-change'));
        }
      } catch (_) {}
    });
  }

  // Enhance category nets pages by appending a "Next:" time per net using the JSON feed
  async function enhanceCategoryNets() {
    const sections = document.querySelectorAll('.nets-section[data-next-net-json]');
    if (!sections.length) return;
    for (const section of sections) {
      const url = section.getAttribute('data-next-net-json');
      if (!url) continue;
      const data = await fetchJSON(url);
      if (!data) {
        if (DIAG) appendDiag(section, 'Live data fetch failed for category nets.');
        continue;
      }
      const arr = getWeekArray(data);
      if (!Array.isArray(arr)) {
        if (DIAG) appendDiag(section, 'Live data loaded but no weekly array found (category nets).');
        continue;
      }
      const now = new Date();
      const byId = new Map();
      arr.forEach((occ) => {
        const sid = (occ && occ.id) || null;
        const siso = getStartISO(occ);
        if (!sid || !siso) return;
        try { if (new Date(siso) < now) return; } catch (_) { return; }
        const prev = byId.get(sid);
        if (!prev || new Date(getStartISO(occ)) < new Date(getStartISO(prev))) byId.set(sid, occ);
      });
      section.querySelectorAll('.net-next-when[data-net-id]').forEach((slot) => {
        const id = slot.getAttribute('data-net-id');
        if (!id) return;
        const occ = byId.get(id);
        if (!occ) { slot.textContent = ''; return; }
        const start = getStartISO(occ);
        const label = (TIME_VIEW === 'my') ? 'Local' : (tzDisplay(occ.time_zone || '') || tzFromISO(start));
        const whenText = (TIME_VIEW === 'my') ? fmtWeekWhen(start || '') : formatISOAsWritten(start || '');
        // Write " — Next: ... <tz>"
        slot.textContent = ` — Next: ${whenText} `;
        const tz = document.createElement('span');
        tz.className = 'next-net-tz';
        tz.textContent = label;
        slot.appendChild(tz);
        if (SHOW_UTC) {
          const utc = document.createElement('span');
          utc.className = 'next-net-utc';
          utc.textContent = ` · ${fmtUTC(start)}`;
          slot.appendChild(utc);
        }
      });
      if (DIAG) appendDiag(section, 'Live data loaded. Category nets updated.');

      // Compute a unified tz (if any) across the next occurrences by id
      try {
        const uniq = new Set();
        let sample = null;
        byId.forEach((occ) => {
          const tz = (occ && occ.time_zone) || '';
          if (tz) {
            uniq.add(tz);
            if (!sample) sample = occ;
          }
        });
        if (uniq.size === 1 && sample) {
          const tzIana = sample.time_zone;
          const tzName = tzDisplay(tzIana) || '';
          const abbr = tzAbbr(tzIana, getStartISO(sample));
          if (tzName) section.dataset.tzName = tzName;
          if (abbr) section.dataset.tzAbbr = abbr;
        } else {
          // No single tz; clear any previous context
          delete section.dataset.tzName;
          delete section.dataset.tzAbbr;
        }
        document.dispatchEvent(new CustomEvent('bhn:tzcontext-change'));
      } catch (_) {}
    }
  }

  function init() {
    enhanceNextNet();
    enhanceWeekList();
    enhanceNcoTable();
    // Category nets (BHN/Disability/General pages)
    enhanceCategoryNets();

  // Re-render on time view change
  document.addEventListener('bhn:timeview-change', () => {
    try {
      const v = localStorage.getItem('timeView:global');
      TIME_VIEW = (v === 'my') ? 'my' : 'net';
      SHOW_UTC = localStorage.getItem('timeView:showUTC') === '1';
    } catch (_) { TIME_VIEW = 'net'; }
    // Re-run hydration for sections on page; cache prevents extra network
    enhanceNextNet();
    enhanceWeekList();
    enhanceCategoryNets();
  });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
