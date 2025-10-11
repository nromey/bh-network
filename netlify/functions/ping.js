// Minimal sanity check for Netlify Functions (ESM)
export async function handler() {
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ ok: true, time: new Date().toISOString() })
  };
}
