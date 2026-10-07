// La app avisa de que ya aplicó un pago confirmado (paid -> applied) para no repetirlo.

const { db, enc } = require('./_db');
const { sendJson } = require('./_stripe');
const { requireAuth } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'client') return sendJson(res, 403, { error: 'No permitido' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    const ref = String(body.ref || '');
    await db('PATCH', `payments?ref=eq.${enc(ref)}&client_id=eq.${enc(auth.id)}&status=eq.paid`,
      { status: 'applied', updated_at: new Date().toISOString() }, 'return=minimal');
    return sendJson(res, 200, { ok: true });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'Error' });
  }
};
