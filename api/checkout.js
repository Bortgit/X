// Crea una sesión de pago de Stripe Checkout.
// El precio SIEMPRE se calcula aquí, nunca se fía del importe que mande la app.

const { stripe, originFor, sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth } = require('./_auth');

const MAX_DATA_BYTES = 20000;

const MEMBERSHIP_CENTS = 800; // 8 €/mes
const RESID_FIRST_DOG = 2000; // 20 €/noche
const RESID_SECOND_DOG = 1000; // 10 €/noche (si van juntos)
const GUARDERIA_PER_DOG_WEEK = 3500; // 35 €/semana por perro

const SERVICES = {
  ind1: { name: 'Sesión individual', cents: 3000 },
  bono2: { name: 'Bono 2 sesiones', cents: 5000 },
  bono4: { name: 'Bono 4 sesiones', cents: 8000 },
  diyg: { name: 'DIY grupal (mensual)', cents: 10000 },
  videocall: { name: 'Sesión por videollamada', cents: 1500 },
};

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const REF_RE = /^[A-Za-z0-9_-]{6,64}$/;

function nightsBetween(checkin, checkout) {
  if (!DATE_RE.test(checkin) || !DATE_RE.test(checkout)) return 0;
  const a = Date.parse(checkin + 'T00:00:00Z');
  const b = Date.parse(checkout + 'T00:00:00Z');
  if (!Number.isFinite(a) || !Number.isFinite(b)) return 0;
  return Math.round((b - a) / 86400000);
}

function intIn(value, min, max) {
  const n = Number(value);
  return Number.isInteger(n) && n >= min && n <= max ? n : null;
}

// Devuelve { name, cents } o lanza un error con mensaje para el cliente.
function priceFor(body) {
  switch (body.kind) {
    case 'membership':
      return { name: 'BalancedDog Club — suscripción mensual', cents: MEMBERSHIP_CENTS };
    case 'training':
    case 'diy': {
      const svc = SERVICES[body.service];
      if (!svc) throw new Error('Servicio no válido');
      if (body.kind === 'diy' && body.service !== 'diyg') throw new Error('Servicio no válido');
      if (body.kind === 'training' && body.service === 'diyg') throw new Error('Servicio no válido');
      return { name: svc.name, cents: svc.cents };
    }
    case 'residence': {
      const nights = nightsBetween(body.checkin, body.checkout);
      const dogs = intIn(body.dogCount, 1, 2);
      if (nights < 1 || nights > 90 || !dogs) throw new Error('Fechas o perros no válidos');
      const perNight = dogs === 2 ? RESID_FIRST_DOG + RESID_SECOND_DOG : RESID_FIRST_DOG;
      return { name: `Residencia canina — ${nights} noche(s), ${dogs} perro(s)`, cents: nights * perNight };
    }
    case 'guarderia': {
      const weeks = intIn(body.weekCount, 1, 26);
      const dogs = intIn(body.dogCount, 1, 2);
      if (!weeks || !dogs) throw new Error('Semanas o perros no válidos');
      return { name: `Guardería de mañana — ${weeks} semana(s), ${dogs} perro(s)`, cents: weeks * dogs * GUARDERIA_PER_DOG_WEEK };
    }
    default:
      throw new Error('Tipo de pago no válido');
  }
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'client') return sendJson(res, 403, { error: 'Solo los clientes pueden pagar' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    if (!REF_RE.test(String(body.ref || ''))) throw new Error('Referencia no válida');

    const { name, cents: baseCents } = priceFor(body);

    // El descuento por XP lo calcula la app (los XP viven en el móvil del cliente);
    // aquí solo se limita para que nunca sea negativo ni supere el precio.
    let discount = Math.round(Number(body.discountCents) || 0);
    // La membresía y el DIY son suscripciones con precio fijo: nunca llevan descuento.
    if (body.kind === 'membership' || body.kind === 'diy') discount = 0;
    discount = Math.max(0, Math.min(discount, baseCents));
    const finalCents = baseCents - discount;

    if (finalCents === 0) return sendJson(res, 200, { free: true });
    if (finalCents < 50) throw new Error('El importe mínimo de cobro es 0,50 €');

    const isSub = body.kind === 'membership' || body.kind === 'diy';
    const origin = originFor(req);

    // Datos del cliente solo para que tú los veas en el panel de Stripe y puedas
    // localizar cualquier pago (nombre y teléfono salen de la cuenta guardada en el servidor).
    const clean = (v, n) => String(v || '').replace(/[\r\n]+/g, ' ').trim().slice(0, n);
    const rows = await db('GET', `clients?select=phone,data&id=eq.${enc(auth.id)}`);
    if (!rows.length) throw new Error('Cuenta no encontrada');
    const clientName = clean(rows[0].data && rows[0].data.name, 100);
    const clientPhone = clean(rows[0].phone, 30);
    const metadata = {
      kind: body.kind, ref: body.ref, client_id: auth.id, base_cents: baseCents, discount_cents: discount,
      cliente: clientName, telefono: clientPhone,
    };
    const description = `${name} — ${clientName} ${clientPhone}`.slice(0, 300);

    const session = await stripe('POST', '/checkout/sessions', {
      mode: isSub ? 'subscription' : 'payment',
      locale: 'es',
      client_reference_id: body.ref,
      success_url: `${origin}/?pago=ok&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/?pago=cancelado`,
      line_items: [
        {
          quantity: 1,
          price_data: Object.assign(
            { currency: 'eur', unit_amount: finalCents, product_data: { name } },
            isSub ? { recurring: { interval: 'month' } } : {}
          ),
        },
      ],
      metadata,
      ...(isSub
        ? { subscription_data: { description, metadata } }
        : { payment_intent_data: { description, metadata } }),
    });

    // Se guarda en el servidor qué se estaba comprando, para poder aplicarlo aunque
    // el cliente cierre la app antes de volver de Stripe.
    let data = body.applyData && typeof body.applyData === 'object' ? body.applyData : {};
    if (JSON.stringify(data).length > MAX_DATA_BYTES) data = {};
    await db('POST', 'payments', [{ ref: body.ref, client_id: auth.id, kind: body.kind, data, session_id: session.id, status: 'created' }], 'return=minimal');

    return sendJson(res, 200, { url: session.url });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || 'No se pudo iniciar el pago' });
  }
};
