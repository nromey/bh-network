const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store, max-age=0',
  'Access-Control-Allow-Origin': '*',
};

const TARGET_URL =
  process.env.BHN_SUGGEST_TARGET ||
  'https://data.blindhams.network/nets-helper/api/public/suggest';

function buildAuthHeader() {
  const precomputed = (process.env.BHN_SUGGEST_AUTH_HEADER || '').trim();
  if (precomputed) {
    return precomputed;
  }

  const user = (process.env.BHN_SUGGEST_AUTH_USER || '').trim();
  const password = process.env.BHN_SUGGEST_AUTH_PASS;
  if (!user) {
    return '';
  }
  const safePassword = password === undefined ? '' : password;
  const encoded = Buffer.from(`${user}:${safePassword}`, 'utf8').toString('base64');
  return `Basic ${encoded}`;
}

const AUTH_HEADER = buildAuthHeader();

function extractClientIp(headers) {
  const lowercase = {};
  Object.entries(headers || {}).forEach(([key, value]) => {
    lowercase[key.toLowerCase()] = value;
  });
  return (
    lowercase['x-forwarded-for'] ||
    lowercase['client-ip'] ||
    lowercase['x-real-ip'] ||
    lowercase['x-nf-client-connection-ip'] ||
    ''
  );
}

function respond(statusCode, bodyObject) {
  const hasBody = bodyObject !== undefined && bodyObject !== null;
  return {
    statusCode,
    headers: JSON_HEADERS,
    body: hasBody ? JSON.stringify(bodyObject) : '',
  };
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return respond(405, { error: 'method_not_allowed' });
  }

  let payload;
  try {
    payload = event.body ? JSON.parse(event.body) : {};
  } catch (error) {
    return respond(400, { error: 'invalid_json', message: 'Request body must be valid JSON.' });
  }

  const fetchHeaders = new Headers({ 'Content-Type': 'application/json' });
  if (AUTH_HEADER) {
    fetchHeaders.set('Authorization', AUTH_HEADER);
  }
  const clientIp = extractClientIp(event.headers || {});
  if (clientIp) {
    fetchHeaders.set('X-Forwarded-For', clientIp);
  }

  let upstreamResponse;
  try {
    upstreamResponse = await fetch(TARGET_URL, {
      method: 'POST',
      headers: fetchHeaders,
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return respond(502, { error: 'upstream_error', message: String(error?.message || error) });
  }

  if (upstreamResponse.status === 204) {
    return respond(204);
  }

  const responseText = await upstreamResponse.text();
  let responseBody;
  if (responseText) {
    try {
      responseBody = JSON.parse(responseText);
    } catch (error) {
      responseBody = { message: responseText };
    }
  } else {
    responseBody = {};
  }

  return {
    statusCode: upstreamResponse.status,
    headers: JSON_HEADERS,
    body: JSON.stringify(responseBody),
  };
};
