// Netlify Function: proxy-next-nets
// Purpose: Avoid client-side CORS issues by fetching the Next Nets JSON server-side.
// Only used on dev branch (jekyll.environment == 'development').

const jsonHeaders = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store, max-age=0',
  'Access-Control-Allow-Origin': '*',
};

const FEED_URL_DEFAULT = 'https://data.blindhams.network/next_nets.json';

export const handler = async (event) => {
  try {
    const url = new URL(event.rawUrl || 'http://localhost');
    const src = url.searchParams.get('url') || FEED_URL_DEFAULT;
    const resp = await fetch(src, { headers: { 'Accept': 'application/json' }, redirect: 'follow', cache: 'no-store' });
    if (!resp.ok) {
      return { statusCode: 502, headers: jsonHeaders, body: JSON.stringify({ error: 'bad_gateway', status: resp.status, statusText: resp.statusText }) };
    }
    const data = await resp.json();
    return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify(data) };
  } catch (e) {
    return { statusCode: 200, headers: jsonHeaders, body: JSON.stringify({ error: 'proxy_error', message: String(e && e.message || e) }) };
  }
};

