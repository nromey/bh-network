// assets/js/solar-card.js
// Hydrate the home solar card with live data from solar.json
(function () {
  if (typeof window === 'undefined') return;
  if (window.BHN_SOLAR_CARD_INIT) return;
  window.BHN_SOLAR_CARD_INIT = true;

  const DEFAULT_TZ = 'America/New_York';
  const HIDE_KEY = 'bhn:solar:hidden';
  const VIEW_KEY = 'bhn:solar:view';
  const TIME_KEY = 'timeView:global';
  const UTC_KEY = 'timeView:showUTC';
  const DIAG = (() => {
    try { return new URLSearchParams(window.location.search).get('diag') === '1'; }
    catch (_) { return false; }
  })();

  const wrappers = document.querySelectorAll('[data-solar-wrapper]');
  if (!wrappers.length) return;

  function loadHide() {
    try { return localStorage.getItem(HIDE_KEY) === '1'; } catch (_) { return false; }
  }
  function saveHide(flag) {
    try { localStorage.setItem(HIDE_KEY, flag ? '1' : '0'); } catch (_) {}
  }
  function loadViewPref() {
    try {
      const val = localStorage.getItem(VIEW_KEY);
      return val === 'table' ? 'table' : 'headings';
    } catch (_) { return 'headings'; }
  }
  function saveViewPref(view) {
    try { localStorage.setItem(VIEW_KEY, view); } catch (_) {}
  }
  function getTimeView() {
    try { return localStorage.getItem(TIME_KEY) === 'my' ? 'my' : 'net'; }
    catch (_) { return 'net'; }
  }
  function showUTCEnabled() {
    try { return localStorage.getItem(UTC_KEY) === '1'; } catch (_) { return false; }
  }

  function appendDiag(container, text) {
    if (!DIAG || !container) return;
    container.hidden = false;
    const p = document.createElement('p');
    p.textContent = String(text);
    container.appendChild(p);
  }

  function describeKp(kp) {
    if (kp === null || kp === undefined) return null;
    const val = Number(kp);
    if (!Number.isFinite(val)) return null;
    if (val < 2) return 'Quiet';
    if (val < 3) return 'Unsettled';
    if (val < 4) return 'Active';
    if (val < 5) return 'Minor storm levels';
    if (val < 6) return 'Moderate storm levels';
    if (val < 7) return 'Strong storm levels';
    if (val < 8) return 'Severe storm levels';
    return 'Extreme storm levels';
  }

  function fmtNumber(value, digits = 0) {
    if (value === null || value === undefined) return null;
    const num = Number(value);
    if (!Number.isFinite(num)) return null;
    return num.toFixed(digits);
  }

  function formatUTC(iso) {
    try {
      const d = new Date(iso);
      const time = d.toLocaleTimeString(undefined, { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false });
      return `UTC ${time}`;
    } catch (_) {
      return '';
    }
  }

  function tzLabel(iana) {
    try {
      if (!iana) return '';
      const d = new Date();
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'longGeneric' }).formatToParts(d);
      const name = parts.find((p) => p.type === 'timeZoneName');
      if (name) return name.value;
    } catch (_) { /* ignore */ }
    try {
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: iana, timeZoneName: 'long' }).formatToParts(new Date());
      const name = parts.find((p) => p.type === 'timeZoneName');
      if (name) return name.value;
    } catch (_) {}
    return '';
  }

  function formatTimeForView(iso, view) {
    if (!iso) return { text: '—', tz: '' };
    const opts = { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' };
    try {
      if (view === 'my') {
        const text = new Date(iso).toLocaleString(undefined, opts);
        return { text, tz: 'Local time' };
      }
      const text = new Date(iso).toLocaleString(undefined, { ...opts, timeZone: DEFAULT_TZ });
      const tz = tzLabel(DEFAULT_TZ) || 'Eastern';
      return { text, tz };
    } catch (_) {
      return { text: iso, tz: '' };
    }
  }

  function pluralize(value, unit) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    const rounded = Math.round(n);
    return `${rounded} ${unit}${rounded === 1 ? '' : 's'}`;
  }

  function formatMetricTimeTag(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return '';
      const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' });
      return `${time} UTC`;
    } catch (_) {
      return '';
    }
  }

  function formatKValue(num) {
    const value = Number(num);
    if (!Number.isFinite(value)) return null;
    const rounded = Math.round(value * 100) / 100;
    return (Math.abs(rounded % 1) < 1e-6) ? String(rounded.toFixed(0)) : String(rounded.toFixed(2));
  }

  async function fetchJSON(url) {
    try {
      const resp = await fetch(url, { credentials: 'omit', cache: 'no-store' });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return await resp.json();
    } catch (err) {
      console.warn('[bhn] solar card fetch failed', err);
      return null;
    }
  }

  wrappers.forEach((wrapper) => {
    const card = wrapper.querySelector('[data-solar-card]');
    if (!card) return;
    const hiddenMsg = wrapper.querySelector('[data-solar-hidden]');
    const hideForm = wrapper.querySelector('[data-solar-hide-form]');
    const hideCheckbox = wrapper.querySelector('[data-solar-hide-checkbox]');
    const hideSave = wrapper.querySelector('[data-solar-hide-save]');
    const hideStatus = wrapper.querySelector('[data-solar-hide-status]');
    const showButton = wrapper.querySelector('[data-solar-show]');
    const viewButtons = card.querySelectorAll('[data-solar-view-button]');
    const viewStatus = card.querySelector('[data-solar-view-status]');
    const summary = card.querySelector('[data-solar-summary]');
    const updated = card.querySelector('[data-solar-updated]');
    const diagBox = card.querySelector('[data-solar-diag]');
    const url = card.getAttribute('data-solar-json');
    const state = {
      data: null,
      fetched: false,
      currentView: loadViewPref(),
    };

    function updateHideUI(flag, announce = false) {
      if (hideCheckbox) {
        try { hideCheckbox.checked = !!flag; } catch (_) {}
      }
      if (flag) {
        card.hidden = true;
        if (hiddenMsg) hiddenMsg.hidden = false;
      } else {
        card.hidden = false;
        if (hiddenMsg) hiddenMsg.hidden = true;
      }
      if (announce && hideStatus) {
        hideStatus.textContent = flag ? 'Solar card hidden on this device.' : 'Solar card will show on this device.';
      }
    }

    function applyView(view, announce = false) {
      state.currentView = view;
      viewButtons.forEach((btn) => {
        const isActive = btn.dataset.solarViewButton === view;
        btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });
      card.querySelectorAll('[data-solar-view]').forEach((panel) => {
        const isMatch = panel.getAttribute('data-solar-view') === view;
        panel.hidden = !isMatch;
      });
      if (announce && viewStatus) {
        viewStatus.textContent = view === 'table' ? 'Table view selected.' : 'Headings view selected.';
      }
      saveViewPref(view);
    }

    function updateField(name, text) {
      card.querySelectorAll(`[data-solar-field="${name}"]`).forEach((el) => {
        el.textContent = text || '—';
      });
    }

    function updateNote(name, text) {
      card.querySelectorAll(`[data-solar-note="${name}"]`).forEach((el) => {
        el.textContent = text || '—';
      });
    }

    function updateHeading(name, text) {
      card.querySelectorAll(`[data-solar-heading="${name}"]`).forEach((el) => {
        el.textContent = text || '—';
      });
    }

    function renderTimes() {
      if (!state.data) return;
      if (!updated) return;
      const view = getTimeView();
      const tzInfo = formatTimeForView(state.data.updated, view);
      let text = state.data.updated ? `Updated: ${tzInfo.text}` : 'Updated: —';
      if (tzInfo.tz) text += ` (${tzInfo.tz})`;
      if (showUTCEnabled() && state.data.updated) {
        const utc = formatUTC(state.data.updated);
        if (utc) text += ` · ${utc}`;
      }
      const stale = state.data.stale_minutes;
      if (Number.isFinite(stale)) {
        text += stale > 0 ? ` · ${pluralize(stale, 'minute')} old` : ' · Fresh';
      }
      updated.textContent = text;
    }

    function renderData() {
      if (!state.data) return;
      const now = state.data.now || {};
      const sfi = now.sfi || {};
      const kp = now.k_index || {};
      const midK = now.mid_latitude_k_index || {};
      const apValue = now.a_index;
      const wind = now.solar_wind || {};
      const xray = now.xray || {};
      const sunspot = now.sunspot || {};
      const forecast = (state.data.forecast && state.data.forecast.flare_probability) || {};
      const toNumber = (value) => {
        if (value === undefined || value === null || value === '') return null;
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
      };
      const nf = new Intl.NumberFormat(undefined);

      const sfiVal = fmtNumber(sfi.value);
      const sfiMean = fmtNumber(sfi.ninety_day_mean);
      updateField('sfi', sfiVal ? `${sfiVal}` : '—');
      updateNote('sfi', sfiMean ? `90-day mean ${sfiMean}` : (sfi.schedule ? `Reported (${sfi.schedule})` : '—'));
      let sfiSentence = sfiVal ? `The Solar Flux Index is ${sfiVal}${sfiMean ? ` (90-day mean ${sfiMean}).` : '.'}` : 'Solar flux data unavailable.';

      const sunspotNumber = toNumber(sunspot.number);
      const sunspotArea = toNumber(sunspot.area_10e6);
      const sunspotRegions = toNumber(sunspot.new_regions);
      const sunspotDateRaw = sunspot.observation_date || '';
      const sunspotNumberText = sunspotNumber !== null ? nf.format(sunspotNumber) : null;
      const sunspotAreaText = sunspotArea !== null ? nf.format(sunspotArea) : null;
      updateField('sunspot', sunspotNumberText || '—');
      const sunspotNotes = [];
      if (sunspotAreaText) sunspotNotes.push(`${sunspotAreaText} millionths`);
      if (sunspotRegions !== null) sunspotNotes.push(`${sunspotRegions} new regions`);
      if (sunspotDateRaw) sunspotNotes.push(`Observed ${sunspotDateRaw}`);
      updateNote('sunspot', sunspotNotes.length ? sunspotNotes.join(' · ') : '—');
      let sunspotSentence = 'Sunspot number unavailable.';
      if (sunspotNumberText) {
        const bits = [`Sunspot number is ${sunspotNumberText}`];
        if (sunspotAreaText) bits.push(`area ${sunspotAreaText} millionths`);
        if (sunspotRegions !== null) {
          if (sunspotRegions === 0) bits.push('no new regions');
          else if (sunspotRegions === 1) bits.push('1 new region');
          else bits.push(`${sunspotRegions} new regions`);
        }
        let datePhrase = '';
        if (sunspotDateRaw) {
          try {
            const d = new Date(`${sunspotDateRaw}T00:00:00Z`);
            datePhrase = d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
          } catch (_) {
            datePhrase = sunspotDateRaw;
          }
          if (datePhrase) bits.push(`as of ${datePhrase} UTC`);
        }
        sunspotSentence = `${bits.join(', ')}.`;
      }

      const kpRaw = toNumber(kp.value);
      const kpVal = kpRaw !== null ? formatKValue(kpRaw) : null;
      const kpDesc = kpRaw !== null ? describeKp(kpRaw) : null;
      const kpTimeTag = formatMetricTimeTag(kp.time_tag);
      if (kpVal) {
        updateField('kp', kpVal);
        const kpBits = [];
        if (kp.kp_code) kpBits.push(kp.kp_code);
        if (kpDesc) kpBits.push(kpDesc);
        updateNote('kp', kpBits.length ? kpBits.join(' · ') : '—');
      } else {
        updateField('kp', '—');
        updateNote('kp', '—');
      }
      const apVal = apValue !== undefined && apValue !== null ? String(apValue) : null;
      if (apVal) {
        updateField('ap', apVal);
        updateNote('ap', kpDesc ? `${kpDesc} conditions` : 'Ap derived from Kp');
      } else {
        updateField('ap', '—');
        updateNote('ap', '—');
      }
      const kpSentence = kpVal
        ? `The planetary K index${kpTimeTag ? ` at ${kpTimeTag}` : ''} is ${kpVal}${kpDesc ? ` (${kpDesc.toLowerCase()} conditions)` : ''}.`
        : 'Planetary K index data is unavailable.';
      const apSentence = apVal ? `The planetary A index is ${apVal}.` : 'Planetary A index data is unavailable.';

      const midRaw = toNumber(midK.value);
      const midVal = midRaw !== null ? formatKValue(midRaw) : null;
      const midDesc = midRaw !== null ? describeKp(midRaw) : null;
      const midApVal = toNumber(midK.ap);
      const midTimeTag = formatMetricTimeTag(midK.time_tag);
      if (midVal) {
        updateField('mid_k', midVal);
        const midBits = [];
        if (midK.kp_code) midBits.push(midK.kp_code);
        if (midDesc) midBits.push(midDesc);
        if (midApVal !== null) midBits.push(`A ${midApVal}`);
        updateNote('mid_k', midBits.length ? midBits.join(' · ') : '—');
      } else {
        updateField('mid_k', '—');
        updateNote('mid_k', '—');
      }
      let midSentence = 'Mid-latitude Boulder K index data is unavailable.';
      if (midVal) {
        midSentence = `The mid-latitude Boulder K index${midTimeTag ? ` at ${midTimeTag}` : ''} is ${midVal}${midDesc ? ` (${midDesc.toLowerCase()} conditions)` : ''}.`;
        if (midApVal !== null) midSentence += ` The Boulder A index is ${midApVal}.`;
      }

      const windSpeed = fmtNumber(wind.speed_kms, 0);
      const windDensity = fmtNumber(wind.density, 3);
      const windTemp = fmtNumber(wind.temperature, 0);
      const windParts = [];
      if (windSpeed) windParts.push(`${windSpeed} km/s`);
      if (windDensity) windParts.push(`${windDensity} cm^-3`);
      updateField('wind', windParts.length ? windParts.join(', ') : '—');
      const windNotes = [];
      if (windTemp) windNotes.push(`${windTemp} K`);
      if (wind.spacecraft) windNotes.push(`Source: ${wind.spacecraft}`);
      updateNote('wind', windNotes.length ? windNotes.join(' · ') : '—');
      let windSentence = 'Solar wind data unavailable.';
      if (windSpeed && windDensity) {
        windSentence = `Solar wind speed is ${windSpeed} km/s with density ${windDensity} cm^-3.`;
      } else if (windSpeed) {
        windSentence = `Solar wind speed is ${windSpeed} km/s.`;
      } else if (windDensity) {
        windSentence = `Solar wind density is ${windDensity} cm^-3.`;
      }
      if (windNotes.length) {
        const extra = windNotes.join('; ').replace('Source: ', 'source ');
        windSentence = windSentence.endsWith('.') ? `${windSentence.slice(0, -1)} (${extra}).` : `${windSentence} (${extra}).`;
      }

      const noise = now.noise || {};
      const noisePlanetary = noise.planetary || {};
      const noiseMid = noise.mid_latitude || {};
      const noiseFieldParts = [];
      const noiseNotes = [];
      let noiseSentence = '';
      if (noisePlanetary.description) {
        const sUnits = noisePlanetary.s_units !== undefined && noisePlanetary.s_units !== null ? Number(noisePlanetary.s_units) : null;
        const desc = noisePlanetary.description;
        if (sUnits !== null && sUnits > 0) {
          noiseFieldParts.push(`Planetary +${sUnits} S`);
          noiseSentence = `Planetary noise estimate around plus ${sUnits} S-units (${desc}).`;
        } else {
          noiseFieldParts.push('Planetary baseline');
          noiseSentence = `Planetary noise estimate: ${desc}.`;
        }
        if (noisePlanetary.k_value !== undefined && noisePlanetary.k_value !== null) {
          const formatted = formatKValue(noisePlanetary.k_value);
          if (formatted) noiseNotes.push(`Planetary K ${formatted}`);
        }
        noiseNotes.push(desc);
      }
      if (noiseMid.description) {
        const sUnits = noiseMid.s_units !== undefined && noiseMid.s_units !== null ? Number(noiseMid.s_units) : null;
        const desc = noiseMid.description;
        if (sUnits !== null && sUnits > 0) {
          noiseFieldParts.push(`Boulder +${sUnits} S`);
          noiseSentence = noiseSentence ? `${noiseSentence} Boulder noise around plus ${sUnits} S-units (${desc}).` : `Boulder noise around plus ${sUnits} S-units (${desc}).`;
        } else {
          noiseFieldParts.push('Boulder baseline');
          noiseSentence = noiseSentence ? `${noiseSentence} Boulder noise estimate: ${desc}.` : `Boulder noise estimate: ${desc}.`;
        }
        if (noiseMid.k_value !== undefined && noiseMid.k_value !== null) {
          const formatted = formatKValue(noiseMid.k_value);
          if (formatted) noiseNotes.push(`Boulder K ${formatted}`);
        }
        noiseNotes.push(`Boulder: ${desc}`);
      }
      updateField('noise', noiseFieldParts.length ? noiseFieldParts.join(' / ') : '—');
      updateNote('noise', noiseNotes.length ? noiseNotes.join(' · ') : '—');
      if (!noiseSentence) noiseSentence = 'Noise estimate unavailable.';

      const primaryFlux = toNumber(xray.flux_wm2);
      const primaryFluxDisplay = primaryFlux !== null ? Number(primaryFlux).toExponential(2) : null;
      const xrayClass = xray.classification || '';
      const xrayEnergy = xray.energy || '';
      const xraySatellite = xray.satellite || '';
      const xrayDisplayParts = [];
      if (xrayClass) xrayDisplayParts.push(xrayClass);
      if (primaryFluxDisplay) xrayDisplayParts.push(`${primaryFluxDisplay} W/m²`);
      updateField('xray', xrayDisplayParts.length ? xrayDisplayParts.join(', ') : '—');
      const xrNotes = [];
      if (xrayEnergy) xrNotes.push(xrayEnergy);
      if (xraySatellite) xrNotes.push(`GOES-${xraySatellite}`);
      const xraySecondary = xray.secondary || {};
      const secondaryFlux = toNumber(xraySecondary.flux_wm2);
      const secondaryFluxDisplay = secondaryFlux !== null ? Number(secondaryFlux).toExponential(2) : null;
      if (secondaryFluxDisplay && xraySecondary.energy) {
        xrNotes.push(`${xraySecondary.energy}: ${secondaryFluxDisplay} W/m²`);
      }
      updateNote('xray', xrNotes.length ? xrNotes.join(' · ') : '—');
      let xraySentence = 'X-ray flux data unavailable.';
      if (primaryFluxDisplay || xrayClass) {
        const parts = [];
        parts.push('X-ray flux');
        if (xrayEnergy) parts.push(`on the ${xrayEnergy} band`);
        if (primaryFluxDisplay) parts.push(`is ${primaryFluxDisplay} W/m²`);
        if (xrayClass) parts.push(`class ${xrayClass}`);
        if (xraySatellite) parts.push(`from GOES-${xraySatellite}`);
        xraySentence = parts.join(' ') + '.';
      }
      if (secondaryFluxDisplay) {
        const secondaryClass = xraySecondary.classification ? `, class ${xraySecondary.classification}` : '';
        const band = xraySecondary.energy || 'secondary';
        xraySentence += ` On the ${band} band the flux is ${secondaryFluxDisplay} W/m²${secondaryClass}.`;
      }

      const flareC = forecast.c_class || {};
      const flareM = forecast.m_class || {};
      const flareX = forecast.x_class || {};
      const flareProton = forecast.proton_10mev || {};
      const flareC1 = toNumber(flareC.day1);
      const flareC2 = toNumber(flareC.day2);
      const flareC3 = toNumber(flareC.day3);
      const flareM1 = toNumber(flareM.day1);
      const flareM2 = toNumber(flareM.day2);
      const flareM3 = toNumber(flareM.day3);
      const flareX1 = toNumber(flareX.day1);
      const flareX2 = toNumber(flareX.day2);
      const flareX3 = toNumber(flareX.day3);
      const proton1 = toNumber(flareProton.day1);
      const proton2 = toNumber(flareProton.day2);
      const proton3 = toNumber(flareProton.day3);
      const flareFieldParts = [];
      if (flareC1 !== null) flareFieldParts.push(`C ${flareC1}%`);
      if (flareM1 !== null) flareFieldParts.push(`M ${flareM1}%`);
      if (flareX1 !== null) flareFieldParts.push(`X ${flareX1}%`);
      if (!flareFieldParts.length && proton1 !== null) flareFieldParts.push(`Proton ${proton1}%`);
      updateField('flare', flareFieldParts.length ? flareFieldParts.join(' / ') : '—');
      const flareNotes = [];
      if (flareC2 !== null || flareM2 !== null || flareX2 !== null) {
        flareNotes.push(`Day 2: C ${flareC2 ?? '—'}%, M ${flareM2 ?? '—'}%, X ${flareX2 ?? '—'}%`);
      }
      if (flareC3 !== null || flareM3 !== null || flareX3 !== null) {
        flareNotes.push(`Day 3: C ${flareC3 ?? '—'}%, M ${flareM3 ?? '—'}%, X ${flareX3 ?? '—'}%`);
      }
      if (proton1 !== null || proton2 !== null || proton3 !== null) {
        const p1 = proton1 !== null ? `${proton1}%` : '—';
        const p2 = proton2 !== null ? `${proton2}%` : '—';
        const p3 = proton3 !== null ? `${proton3}%` : '—';
        flareNotes.push(`10 MeV protons: ${p1}, ${p2}, ${p3}`);
      }
      if (forecast.polar_cap_absorption) {
        flareNotes.push(`Polar cap absorption: ${forecast.polar_cap_absorption}`);
      }
      updateNote('flare', flareNotes.length ? flareNotes.join(' · ') : '—');
      let flareSentence = 'Flare probabilities unavailable.';
      const day1Parts = [];
      if (flareC1 !== null) day1Parts.push(`C-class ${flareC1}%`);
      if (flareM1 !== null) day1Parts.push(`M-class ${flareM1}%`);
      if (flareX1 !== null) day1Parts.push(`X-class ${flareX1}%`);
      if (day1Parts.length) {
        flareSentence = `24-hour flare outlook: ${day1Parts.join(', ')}.`;
        if (proton1 !== null) flareSentence += ` Proton event chance ${proton1}%.`;
        if (forecast.polar_cap_absorption) flareSentence += ` Polar cap absorption ${forecast.polar_cap_absorption}.`;
      } else if (proton1 !== null) {
        flareSentence = `Proton event chance ${proton1}%.`;
        if (forecast.polar_cap_absorption) flareSentence += ` Polar cap absorption ${forecast.polar_cap_absorption}.`;
      } else if (forecast.polar_cap_absorption) {
        flareSentence = `Polar cap absorption ${forecast.polar_cap_absorption}.`;
      }

      updateHeading('sfi', sfiSentence);
      updateHeading('sunspot', sunspotSentence);
      updateHeading('kp', kpSentence);
      updateHeading('ap', apSentence);
      updateHeading('mid_k', midSentence);
      updateHeading('noise', noiseSentence);
      updateHeading('wind', windSentence);
      updateHeading('xray', xraySentence);
      updateHeading('flare', flareSentence);

      if (summary) {
        summary.textContent = [sfiSentence, sunspotSentence, kpSentence, apSentence, midSentence, noiseSentence, windSentence, xraySentence, flareSentence].join(' ');
      }

      renderTimes();

      if (diagBox) {
        diagBox.innerHTML = '';
        if (DIAG) {
          appendDiag(diagBox, `Fetched from: ${url}`);
          if (state.data.diagnostics) {
            Object.entries(state.data.diagnostics).forEach(([k, v]) => appendDiag(diagBox, `${k}: ${v}`));
          }
          appendDiag(diagBox, `stale_minutes: ${state.data.stale_minutes ?? '—'}`);
        }
      }

      try {
        const evt = new CustomEvent('bhn:solar-update', { detail: { data: state.data } });
        document.dispatchEvent(evt);
      } catch (_) {}
    }
    async function ensureData() {
      if (state.fetched || !url) return;
      state.fetched = true;
      const data = await fetchJSON(url);
      if (!data) {
        if (summary) summary.textContent = 'Unable to load live solar data.';
        appendDiag(diagBox, 'Fetch failed for solar.json.');
        return;
      }
      state.data = data;
      renderData();
    }

    // Initial setup
    updateHideUI(loadHide());
    applyView(state.currentView);

    if (!loadHide()) ensureData();

    if (hideSave) {
      hideSave.addEventListener('click', () => {
        const flag = !!(hideCheckbox && hideCheckbox.checked);
        saveHide(flag);
        updateHideUI(flag, true);
        if (!flag) ensureData();
      });
    }

    if (showButton) {
      showButton.addEventListener('click', () => {
        saveHide(false);
        updateHideUI(false, true);
        ensureData();
        showButton.focus();
      });
    }

    viewButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const view = btn.dataset.solarViewButton === 'table' ? 'table' : 'headings';
        if (view === state.currentView) return;
        applyView(view, true);
      });
    });

    document.addEventListener('bhn:timeview-change', () => {
      renderTimes();
    });
  });
})();
