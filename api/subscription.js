// Estado y baja de la suscripción mensual (8 €/mes) en Stripe.

const { stripe, sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth } = require('./_auth');

const SUB_RE = /^sub_[A-Za-z0-9]{10,200}$/;

// Un cliente solo puede tocar la suscripción guardada en SU ficha; el admin, cualquiera.
async function allowed(auth, id) {
  if (auth.role === 'admin') return true;
  const rows = await db('GET', `clients?select=data&id=eq.${enc(auth.id)}`);
  return rows.length && rows[0].data && rows[0].data.stripeSubscriptionId === id;
}

module.exports = async (req, res) => {
  const auth = requireAuth(req, res);
  if (!auth) return;
  try {
    if (req.method === 'GET') {
      const url = new URL(req.url, 'https://x.invalid');
      const id = url.searchParams.get('id') || '';
      if (!SUB_RE.test(id)) return sendJson(res, 400, { error: 'Suscripción no válida' });
      if (!(await allowed(auth, id))) return sendJson(res, 403, { error: 'No permitido' });
      const sub = await stripe('GET', '/subscriptions/' + id);
      return sendJson(res, 200, { status: sub.status });
    }

    if (req.method === 'POST') {
      const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
      if (!SUB_RE.test(String(body.id || '')) || body.action !== 'cancel') {
        return sendJson(res, 400, { error: 'Petición no válida' });
      }
      if (!(await allowed(auth, body.id))) return sendJson(res, 403, { error: 'No permitido' });
      const sub = await stripe('DELETE', '/subscriptions/' + body.id);
      return sendJson(res, 200, { status: sub.status });
    }

    return sendJson(res, 405, { error: 'Método no permitido' });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || 'Error con la suscripción' });
  }
};
