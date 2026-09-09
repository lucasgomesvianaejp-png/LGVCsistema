const GOOGLE_LOOKUP = 'https://identitytoolkit.googleapis.com/v1/accounts:lookup';

export async function requireFirebaseUser(req) {
  const header = String(req.headers.authorization || '');
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('missing_bearer_token');
    err.statusCode = 401;
    throw err;
  }

  const apiKey = process.env.FIREBASE_WEB_API_KEY;
  if (!apiKey) {
    const err = new Error('firebase_server_not_configured');
    err.statusCode = 503;
    throw err;
  }

  const response = await fetch(`${GOOGLE_LOOKUP}?key=${encodeURIComponent(apiKey)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idToken: match[1] })
  });
  if (!response.ok) {
    const err = new Error('invalid_firebase_token');
    err.statusCode = 401;
    throw err;
  }
  const body = await response.json();
  const user = body.users?.[0];
  if (!user?.localId) {
    const err = new Error('invalid_firebase_user');
    err.statusCode = 401;
    throw err;
  }

  const allow = String(process.env.LGV_ALLOWED_EMAILS || '')
    .split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
  if (allow.length && !allow.includes(String(user.email || '').toLowerCase())) {
    const err = new Error('forbidden_user');
    err.statusCode = 403;
    throw err;
  }
  return { uid: user.localId, email: user.email || '' };
}
