// Estado y baja de las suscripciones mensuales en Stripe:
//  - la de la app (8 €/mes) y la del DIY grupal (100 €/mes, una por perro apuntado).
// Acciones (POST):
//  - cancel: cancela AHORA (baja de la app, o el admin quitando a alguien del DIY).
//  - cancel_at_period_end: el cliente abandona el DIY; no se le cobra más, pero Stripe mantiene
//    la suscripción hasta el final del mes ya pagado (así su plaza sigue reservada hasta entonces).

const { stripe, sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth } = require('./_auth');

const SUB_RE = /^sub_[A-Za-z0-9]{10,200}$/;

// Un cliente solo puede tocar suscripciones SUYAS (la de su ficha o una de sus pagos reales de
// membresía/DIY); el admin, cualquiera.
async function allowed(auth, id) {
  if (auth.role === 'admin') return true;
  const rows = await db('GET', `clients?select=data&id=eq.${enc(auth.id)}`);
  if (rows.length && rows[0].data && rows[0].data.stripeSubscriptionId === id) return true;
  const pays = await db('GET', `payments?select=ref&client_id=eq.${enc(auth.id)}&subscription_id=eq.${enc(id)}&status=in.(paid,applied)`);
  return pays.length > 0;
}

function summarize(sub) {
  const item = sub.items && sub.items.data && sub.items.data[0];
  const periodEnd = sub.current_period_end || (item && item.current_period_end) || null;
  const cancelling = !!sub.cancel_at_period_end || !!sub.cancel_at;
  return {
    status: sub.status,
    cancelAtPeriodEnd: cancelling,
    periodEnd,
    endsAt: cancelling ? (sub.cancel_at || periodEnd) : null,
  };
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
      return sendJson(res, 200, summarize(sub));
    }

    if (req.method === 'POST') {
      const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
      if (!SUB_RE.test(String(body.id || '')) || !['cancel', 'cancel_at_period_end'].includes(body.action)) {
        return sendJson(res, 400, { error: 'Petición no válida' });
      }
      if (!(await allowed(auth, body.id))) return sendJson(res, 403, { error: 'No permitido' });
      const sub = body.action === 'cancel'
        ? await stripe('DELETE', '/subscriptions/' + body.id)
        : await stripe('POST', '/subscriptions/' + body.id, { cancel_at_period_end: true });
      return sendJson(res, 200, summarize(sub));
    }

    return sendJson(res, 405, { error: 'Método no permitido' });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || 'Error con la suscripción' });
  }
};
