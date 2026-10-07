// Comprueba con Stripe si una sesión de pago está realmente pagada.
// Stripe es la fuente de verdad: la app solo confirma la reserva si esto devuelve paid:true.

const { stripe, sendJson } = require('./_stripe');
const { requireAuth } = require('./_auth');
const { markPaidFromSession, getPayment } = require('./_payments');

const SESSION_RE = /^cs_(live|test)_[A-Za-z0-9]{10,200}$/;

module.exports = async (req, res) => {
  if (req.method !== 'GET') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  try {
    const url = new URL(req.url, 'https://x.invalid');
    const id = url.searchParams.get('session_id') || '';
    if (!SESSION_RE.test(id)) return sendJson(res, 400, { error: 'Sesión no válida' });

    const s = await stripe('GET', '/checkout/sessions/' + id);
    if (auth.role === 'client' && (!s.metadata || s.metadata.client_id !== auth.id)) throw new Error('Este pago no pertenece a tu cuenta');
    const paid = s.payment_status === 'paid';
    let pay = null;
    if (paid) {
      await markPaidFromSession(s);
      pay = s.client_reference_id ? await getPayment(s.client_reference_id) : null;
    }
    return sendJson(res, 200, {
      data: pay ? pay.data : null,
      applied: !!(pay && pay.status === 'applied'),
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
