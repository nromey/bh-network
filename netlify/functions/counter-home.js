// Netlify Function: counter-home (Blobs-backed)
// Increments or fetches a page view counter using Netlify Blobs.
// No third-party calls; durable storage per site/environment.

import { getStore } from '@netlify/blobs';

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
    const url = new URL(event.rawUrl || 'http://localhost');
    const mode = (url.searchParams.get('mode') || 'hit').toLowerCase();
    const diag = url.searchParams.get('diag') === '1';
    const ns = url.searchParams.get('ns');
    const keyParam = url.searchParams.get('key');

    const store = getStore({ name: STORE_NAME });
    const baseKey = ns && keyParam ? `${ns}:${keyParam}` : (keyParam || DEFAULT_KEY);
    const ym = getYearMonth(COUNTER_TZ);
    const monthKey = `${baseKey}:${ym}`;

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
    const body = { value: 0, total: 0, month: 0, ym, tz, source: 'fallback', error: 'server_error', error_message: String((err && err.message) || err) };
    return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify(body) };
  }
};
