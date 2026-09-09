function config() {
  const url = String(process.env.SUPABASE_URL || '').replace(/\/$/, '');
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    const err = new Error('supabase_server_not_configured');
    err.statusCode = 503;
    throw err;
  }
  return { url, key };
}

export async function supabaseGet(path, { count = false } = {}) {
  const { url, key } = config();
  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`,
    Accept: 'application/json'
  };
  if (count) headers.Prefer = 'count=exact';
  const response = await fetch(`${url}/rest/v1/${path}`, { headers });
  const text = await response.text();
  if (!response.ok) {
    const err = new Error(`supabase_error:${response.status}:${text.slice(0, 300)}`);
    err.statusCode = 502;
    throw err;
  }
  let data = [];
  try { data = text ? JSON.parse(text) : []; } catch { data = []; }
  return { data, contentRange: response.headers.get('content-range') || '' };
}
