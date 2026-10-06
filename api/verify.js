// Comprueba con Stripe si una sesión de pago está realmente pagada.
// Stripe es la fuente de verdad: la app solo confirma la reserva si esto devuelve paid:true.

const { stripe, sendJson } = require('./_stripe');

const SESSION_RE = /^cs_(live|test)_[A-Za-z0-9]{10,200}$/;

module.exports = async (req, res) => {
  if (req.method !== 'GET') return sendJson(res, 405, { error: 'Método no permitido' });
  try {
    const url = new URL(req.url, 'https://x.invalid');
    const id = url.searchParams.get('session_id') || '';
    if (!SESSION_RE.test(id)) return sendJson(res, 400, { error: 'Sesión no válida' });

    const s = await stripe('GET', '/checkout/sessions/' + id);
    const paid = s.payment_status === 'paid';
    return sendJson(res, 200, {
      paid,
      ref: s.client_reference_id || null,
      kind: (s.metadata && s.metadata.kind) || null,
      amountCents: s.amount_total,
      subscriptionId: typeof s.subscription === 'string' ? s.subscription : null,
    });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || 'No se pudo comprobar el pago' });
  }
};
