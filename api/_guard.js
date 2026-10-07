// Reglas que el servidor impone a lo que guarda la app de un CLIENTE (el admin queda libre).
// Si algo no cuadra, se corrige al valor anterior y se apunta un aviso para el panel de admin.
// Solo se vigila lo que cuesta dinero o da ventajas: XP, hucha, estado de la suscripción.

const { db, enc } = require('./_db');

const DAILY_XP = 25; // XP que se ganan como máximo cada día
const READING_BONUS_MAX = 1300; // bono de lectura (800, o 1.300 con dos perros)
const MAX_FLAGS = 10;

const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);
const arr = (v) => (Array.isArray(v) ? v : []);

function madridDay(now) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid' }).format(now || new Date());
}

// ctx: { today, readingId, membershipPayments: n, subIds: [..] }
function guardClient(oldData, newData, oldGuard, ctx) {
  const data = Object.assign({}, newData);
  const guard = Object.assign({ day: '', gained: 0, mem_used: 0, flags: [] }, oldGuard || {});
  const flags = [];
  const flag = (m) => flags.push(m);

  // 1) XP mensual: como mucho +25 al día (cuenta todo lo ganado ese día, aunque se haya gastado)
  const oldXp = num(oldData.xpMonthly);
  const base = oldData.xpMonthlyMonth !== data.xpMonthlyMonth ? 0 : oldXp; // al cambiar de mes se reinicia
  const gain = num(data.xpMonthly) - base;
  let gained = guard.day === ctx.today ? num(guard.gained) : 0;
  if (gain > 0) {
    const allowed = Math.max(0, DAILY_XP - gained);
    if (gain > allowed) { data.xpMonthly = base + allowed; flag(`XP mensual: subida de ${gain} no permitida (máx. ${DAILY_XP}/día)`); }
    gained += Math.min(gain, allowed);
  }
  guard.day = ctx.today; guard.gained = gained;

  // 2) Hucha: solo sube al marcar como leída la lectura mensual vigente
  const oldIds = arr(oldData.lecturaClaimedIds);
  const newIds = arr(data.lecturaClaimedIds);
  const added = newIds.filter((i) => !oldIds.includes(i));
  const validAdded = added.filter((i) => ctx.readingId && i === ctx.readingId);
  if (added.length !== validAdded.length) {
    data.lecturaClaimedIds = oldIds.concat(validAdded.slice(0, 1));
    flag('Lectura marcada que no es la vigente');
  }
  const bankGain = num(data.xpBank) - num(oldData.xpBank);
  const bankAllowed = validAdded.length ? READING_BONUS_MAX : 0;
  if (bankGain > bankAllowed) { data.xpBank = num(oldData.xpBank) + bankAllowed; flag(`Hucha: subida de ${bankGain} no permitida`); }

  // 3) Suscripción: de pendiente/baja a activa solo si hay un pago de membresía nuevo
  const s0 = oldData.subscriptionStatus, s1 = data.subscriptionStatus;
  if (s1 === 'active' && s0 !== 'active' && s0 !== 'grace') {
    if (ctx.membershipPayments > num(guard.mem_used)) guard.mem_used = ctx.membershipPayments;
    else { data.subscriptionStatus = s0; flag('Cuenta marcada como activa sin pago de Stripe'); }
  }
  // 4) El id de suscripción de Stripe solo puede ser uno de los pagos reales de este cliente
  if (data.stripeSubscriptionId !== oldData.stripeSubscriptionId && data.stripeSubscriptionId && !ctx.subIds.includes(data.stripeSubscriptionId)) {
    if (oldData.stripeSubscriptionId) data.stripeSubscriptionId = oldData.stripeSubscriptionId; else delete data.stripeSubscriptionId;
    flag('Suscripción de Stripe que no corresponde a esta cuenta');
  }

  if (flags.length) {
    guard.flags = arr(guard.flags).concat(flags.map((m) => ({ at: new Date().toISOString(), msg: m }))).slice(-MAX_FLAGS);
  }
  return { data, guard, flags, corrected: flags.length > 0 };
}

async function loadContext(clientId) {
  const [reading, pays] = await Promise.all([
    db('GET', 'app_settings?select=value&key=eq.reading'),
    db('GET', `payments?select=subscription_id&client_id=eq.${enc(clientId)}&kind=eq.membership&status=in.(paid,applied)`),
  ]);
  return {
    today: madridDay(),
    readingId: reading[0] && reading[0].value ? reading[0].value.id || null : null,
    membershipPayments: pays.length,
    subIds: pays.map((p) => p.subscription_id).filter(Boolean),
  };
}

module.exports = { guardClient, loadContext, madridDay, DAILY_XP };
