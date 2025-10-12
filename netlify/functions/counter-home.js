// Netlify Function: counter-home (Blobs-backed)
// Increments or fetches a page view counter using Netlify Blobs.
// No third-party calls; durable storage per site/environment.

// Configuration via env vars (optional):
//   BLOBS_STORE: store name within Netlify Blobs (default: "counters")
//   DEFAULT_KEY: key name within the store (default: "home")
const STORE_NAME = process.env.BLOBS_STORE || 'counters';
const DEFAULT_KEY = process.env.DEFAULT_KEY || 'home';
const COUNTER_TZ = process.env.COUNTER_TZ || 'America/New_York';

const jsonHeaders = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store, max-age=0',
  'Access-Control-Allow-Origin': '*',
};

function getYearMonth(tz) {
  const now = new Date();
  try {
    const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit' });
    const parts = fmt.formatToParts(now);
    const y = parts.find(p => p.type === 'year')?.value || String(now.getUTCFullYear());
    const m = parts.find(p => p.type === 'month')?.value || String(now.getUTCMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  } catch (_) {
    return now.toISOString().slice(0, 7);
  }
}

export const handler = async (event) => {
  try {
    // Lazy-load blobs SDK to avoid top-level import crashes
    // if the runtime/bundler isn't ready. This allows us to return
    // diagnostics instead of a 502 from a module load failure.
    const { getStore } = await import('@netlify/blobs');
    const url = new URL(event.rawUrl || 'http://localhost');
    const mode = (url.searchParams.get('mode') || 'hit').toLowerCase();
    const diag = url.searchParams.get('diag') === '1';
    const ns = url.searchParams.get('ns');
    const keyParam = url.searchParams.get('key');

    // Prefer automatic Netlify runtime configuration. If Blobs is not
    // auto-configured for this site, allow manual credentials via env vars.
    // Provide both values or neither:
    //   BLOBS_SITE_ID (or NETLIFY_SITE_ID) and BLOBS_TOKEN
    const siteID = process.env.BLOBS_SITE_ID || process.env.NETLIFY_SITE_ID;
    const token = process.env.BLOBS_TOKEN || process.env.NETLIFY_BLOBS_TOKEN;
    const store = (siteID && token)
      ? getStore({ name: STORE_NAME, siteID, token })
      : getStore({ name: STORE_NAME });
    const baseKey = ns && keyParam ? `${ns}:${keyParam}` : (keyParam || DEFAULT_KEY);
    const ym = getYearMonth(COUNTER_TZ);
    const monthKey = `${baseKey}:${ym}`;

    if (mode === 'list') {
      if (!diag) {
        return { statusCode: 400, headers: jsonHeaders, body: JSON.stringify({ error: 'diag_required' }) };
      }
      const prefix = ns ? `${ns}:` : (keyParam ? String(keyParam) : '');
      const keys = [];
      try {
        let cursor = undefined;
        do {
          // list returns { blobs: [{ key, size, etag, uploadedAt }], cursor }
          const res = await store.list({ prefix, cursor, limit: 100 });
          if (res && Array.isArray(res.blobs)) {
            for (const b of res.blobs) keys.push(b.key);
          }
          cursor = res && res.cursor ? res.cursor : undefined;
        } while (cursor && keys.length < 1000);
      } catch (e) {
        return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ list: [], count: 0, prefix, ym, tz: COUNTER_TZ, source: 'fallback', error: 'list_error', error_message: String(e && e.message || e) }) };
      }
      return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ list: keys, count: keys.length, prefix, ym, tz: COUNTER_TZ, source: 'ok' }) };
    }

    if (mode === 'purge') {
      if (!diag) {
        return { statusCode: 400, headers: jsonHeaders, body: JSON.stringify({ error: 'diag_required' }) };
      }
      // Safety guard: require either ns or key prefix to avoid wiping entire store accidentally.
      const prefix = ns ? `${ns}:` : (keyParam ? String(keyParam) : '');
      if (!prefix) {
        return { statusCode: 400, headers: jsonHeaders, body: JSON.stringify({ error: 'prefix_required', note: 'Provide ns=... or key=... to limit purge scope' }) };
      }
      const toDelete = [];
      try {
        let cursor = undefined;
        do {
          const res = await store.list({ prefix, cursor, limit: 100 });
          if (res && Array.isArray(res.blobs)) {
            for (const b of res.blobs) toDelete.push(b.key);
          }
          cursor = res && res.cursor ? res.cursor : undefined;
        } while (cursor && toDelete.length < 5000);
      } catch (e) {
        return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ purged: 0, attempted: 0, prefix, ym, tz: COUNTER_TZ, source: 'fallback', error: 'list_error', error_message: String(e && e.message || e) }) };
      }
      let purged = 0;
      for (const k of toDelete) {
        try { await store.delete(k); purged++; } catch (_) { /* ignore */ }
      }
      return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ purged, attempted: toDelete.length, prefix, ym, tz: COUNTER_TZ, source: 'ok' }) };
    }

    if (mode === 'get') {
      const totalData = await store.getJSON(baseKey);
      const monthData = await store.getJSON(monthKey);
      const total = totalData && typeof totalData.value === 'number' ? totalData.value : 0;
      const month = monthData && typeof monthData.value === 'number' ? monthData.value : 0;
      const body = { value: total, total, month, ym, tz: COUNTER_TZ, source: 'ok' };
      return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify(diag ? body : { value: body.value, total: body.total, month: body.month }) };
    }

    if (!(mode === 'hit' || mode === 'inc')) {
      return { statusCode: 400, headers: jsonHeaders, body: JSON.stringify({ error: 'bad_mode' }) };
    }
    const [totalCurrent, monthCurrent] = await Promise.all([
      store.getJSON(baseKey),
      store.getJSON(monthKey),
    ]);
    let total = totalCurrent && typeof totalCurrent.value === 'number' ? totalCurrent.value : 0;
    let month = monthCurrent && typeof monthCurrent.value === 'number' ? monthCurrent.value : 0;
    total += 1;
    month += 1;
    await Promise.all([
      store.setJSON(baseKey, { value: total }),
      store.setJSON(monthKey, { value: month }),
    ]);
    const body = { value: total, total, month, ym, tz: COUNTER_TZ, source: 'ok' };
    return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify(diag ? body : { value: body.value, total: body.total, month: body.month }) };
  } catch (err) {
    const tz = COUNTER_TZ;
    const ym = new Date().toISOString().slice(0, 7);
    const runtime = {
      node: process.version,
      netlify: !!process.env.NETLIFY,
      blobs_context: !!process.env.NETLIFY_BLOBS_CONTEXT,
      site_id_present: !!(process.env.BLOBS_SITE_ID || process.env.NETLIFY_SITE_ID),
      token_present: !!(process.env.BLOBS_TOKEN || process.env.NETLIFY_BLOBS_TOKEN),
    };
    const body = { value: 0, total: 0, month: 0, ym, tz, source: 'fallback', error: 'server_error', error_message: String((err && err.message) || err) };
    if (event && event.queryStringParameters && event.queryStringParameters.diag === '1') {
      body.runtime = runtime;
    }
    return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify(body) };
  }
};
    if (mode === 'env') {
      if (!diag) {
        return { statusCode: 400, headers: jsonHeaders, body: JSON.stringify({ error: 'diag_required' }) };
      }
      const runtime = {
        node: process.version,
        netlify: !!process.env.NETLIFY,
        blobs_context: !!process.env.NETLIFY_BLOBS_CONTEXT,
        site_id_present: !!(process.env.BLOBS_SITE_ID || process.env.NETLIFY_SITE_ID),
        token_present: !!(process.env.BLOBS_TOKEN || process.env.NETLIFY_BLOBS_TOKEN),
      };
      return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ ok: true, runtime }) };
    }
