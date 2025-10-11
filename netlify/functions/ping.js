// Minimal sanity check for Netlify Functions
exports.handler = async () => {
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ ok: true, time: new Date().toISOString() })
  };
};

