// Aviso automático de Stripe ("checkout.session.completed"). Así el pago queda registrado
// aunque el cliente cierre la app antes de volver. No se fía del contenido recibido:
// vuelve a pedir el evento a Stripe con nuestra clave y solo usa lo que Stripe devuelve.

const { stripe, sendJson } = require('./_stripe');
const { markPaidFromSession } = require('./_payments');

const EVT_RE = /^evt_[A-Za-z0-9]{10,200}$/;
const OK_TYPES = ['checkout.session.completed', 'checkout.session.async_payment_succeeded'];

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    if (!EVT_RE.test(String(body.id || ''))) return sendJson(res, 400, { error: 'Evento no válido' });
    const evt = await stripe('GET', '/events/' + body.id);
    if (OK_TYPES.includes(evt.type) && evt.data && evt.data.object) {
      await markPaidFromSession(evt.data.object);
    }
    return sendJson(res, 200, { received: true });
  } catch (e) {
    // Error de nuestro lado: Stripe reintentará el aviso.
    return sendJson(res, 500, { error: e.message || 'Error' });
  }
};
