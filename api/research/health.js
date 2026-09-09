import { requireFirebaseUser } from '../_lib/auth.js';
import { json, methodNotAllowed } from '../_lib/http.js';
import { supabaseGet } from '../_lib/supabase-rest.js';

export default async function handler(req, res) {
  if (req.method !== 'GET') return methodNotAllowed(res);
  try {
    await requireFirebaseUser(req);
    const result = await supabaseGet(
      'lgv_ingestion_runs?select=id,source,status,started_at,finished_at,rows_read,rows_written,error_message&order=started_at.desc&limit=30'
    );
    return json(res, 200, { ok: true, runs: result.data });
  } catch (error) {
    return json(res, error.statusCode || 500, { ok: false, error: error.message || 'internal_error' });
  }
}
