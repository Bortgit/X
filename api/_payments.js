// Registro de pagos en el servidor: así un pago no se pierde aunque el cliente cierre la app.
// Estados: created (sesión de Stripe creada) -> paid (Stripe confirma) -> applied (la app ya lo aplicó).

const { db, enc } = require('./_db');

// Marca como pagado un pago a partir de una sesión de Stripe ya verificada por nosotros.
async function markPaidFromSession(s) {
  if (!s || s.payment_status !== 'paid' || !s.client_reference_id) return null;
  const rows = await db('PATCH', `payments?ref=eq.${enc(s.client_reference_id)}&status=eq.created`, {
    status: 'paid',
    session_id: s.id,
    subscription_id: typeof s.subscription === 'string' ? s.subscription : null,
    amount_cents: s.amount_total,
    updated_at: new Date().toISOString(),
  }, 'return=representation');
  return rows && rows[0] ? rows[0] : null;
}

async function getPayment(ref) {
  const rows = await db('GET', `payments?select=ref,client_id,kind,data,status,subscription_id&ref=eq.${enc(ref)}`);
  return rows[0] || null;
}

module.exports = { markPaidFromSession, getPayment };
