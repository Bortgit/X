// Crear cuenta, entrar como cliente y entrar como admin. Devuelve un token de sesión.

const { db, enc } = require('./_db');
const { sendJson } = require('./_stripe');
const { passwordProblem, signToken, hashPassword, checkPassword, adminPasswordOk, normPhone, sleep } = require('./_auth');

const ID_RE = /^[A-Za-z0-9_-]{3,64}$/;

// Una cuenta nueva siempre empieza vacía: sin XP, sin reservas y pendiente de pago.
function stripSecrets(c) {
  const d = Object.assign({}, c);
  delete d.passwordSalt;
  delete d.passwordHash;
  delete d.stripeSubscriptionId;
  d.subscriptionStatus = 'pending';
  d.xpMonthly = 0; d.xpBank = 0; d.streak = Math.min(Number(d.streak) || 0, 1);
  d.lecturaClaimedIds = [];
  d.bookingsTraining = []; d.bookingsResidencia = []; d.bookingsGuarderia = [];
  return d;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};

    if (body.action === 'admin') {
      if (!adminPasswordOk(body.password)) { await sleep(600); return sendJson(res, 401, { error: 'Contraseña incorrecta.' }); }
      return sendJson(res, 200, { token: signToken({ role: 'admin' }), role: 'admin' });
    }

    if (body.action === 'login') {
      const phone = normPhone(body.phone);
      const rows = await db('GET', 'clients?select=id,pass_hash,must_change&phone=eq.' + enc(phone));
      if (!rows.length) { await sleep(600); return sendJson(res, 401, { error: 'No existe ninguna cuenta con ese teléfono.' }); }
      if (!(await checkPassword(body.password, rows[0].pass_hash))) { await sleep(600); return sendJson(res, 401, { error: 'Contraseña incorrecta.' }); }
      return sendJson(res, 200, { token: signToken({ role: 'client', id: rows[0].id }), role: 'client', id: rows[0].id, mustChange: !!rows[0].must_change });
    }

    if (body.action === 'signup') {
      const c = body.client || {};
      const phone = normPhone(c.phone);
      if (!ID_RE.test(String(c.id || '')) || !phone || !String(c.name || '').trim()) throw new Error('Datos de cuenta no válidos');
      const pwBad = passwordProblem(body.password);
      if (pwBad) throw new Error(pwBad);
      const pass_hash = await hashPassword(body.password);
      try {
        await db('POST', 'clients', [{ id: c.id, phone, pass_hash, data: stripSecrets(c), rev: 1 }], 'return=minimal');
      } catch (e) {
        if (e.code === '23505') return sendJson(res, 409, { error: 'Ya existe una cuenta con ese teléfono. Inicia sesión en su lugar.' });
        throw e;
      }
      return sendJson(res, 200, { token: signToken({ role: 'client', id: c.id }), role: 'client', id: c.id, rev: 1 });
    }

    return sendJson(res, 400, { error: 'Petición no válida' });
  } catch (e) {
    return sendJson(res, 400, { error: e.message || 'Error de acceso' });
  }
};
