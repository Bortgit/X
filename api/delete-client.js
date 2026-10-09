// El admin elimina una cuenta de cliente. Si tiene suscripción activa en Stripe, se cancela primero
// para no seguir cobrándole. Los pagos ya hechos se conservan como registro.

const { stripe, sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth } = require('./_auth');

const SUB_RE = /^sub_[A-Za-z0-9]{10,200}$/;

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'admin') return sendJson(res, 403, { error: 'Solo el administrador puede eliminar cuentas' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    const id = String(body.id || '');
    if (!id) return sendJson(res, 400, { error: 'Falta la cuenta' });
    const rows = await db('GET', `clients?select=id,data&id=eq.${enc(id)}`);
    if (!rows.length) return sendJson(res, 200, { ok: true, already: true });

    let cancelled = false;
    const sub = rows[0].data && rows[0].data.stripeSubscriptionId;
    if (sub && SUB_RE.test(sub)) {
      try { await stripe('DELETE', '/subscriptions/' + sub); cancelled = true; }
      catch (e) {
        // Si Stripe dice que ya no existe o ya estaba cancelada, seguimos; cualquier otro fallo detiene el borrado.
        if (!/no such subscription|already been canceled|resource_missing/i.test(e.message || '')) {
          return sendJson(res, 502, { error: 'No se pudo cancelar la suscripción en Stripe; la cuenta NO se ha eliminado. ' + (e.message || '') });
        }
      }
    }
    await db('DELETE', `clients?id=eq.${enc(id)}`, undefined, 'return=minimal');
    return sendJson(res, 200, { ok: true, subscriptionCancelled: cancelled });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo eliminar la cuenta' });
  }
};
