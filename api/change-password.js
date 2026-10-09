// Un cliente cambia su propia contraseña (necesita la actual).

const { sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth, hashPassword, checkPassword, sleep } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'client') return sendJson(res, 403, { error: 'Solo los clientes cambian su contraseña aquí' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    if (String(body.next || '').length < 6) return sendJson(res, 400, { error: 'La contraseña nueva debe tener al menos 6 caracteres.' });
    const rows = await db('GET', `clients?select=pass_hash&id=eq.${enc(auth.id)}`);
    if (!rows.length) return sendJson(res, 401, { error: 'La cuenta ya no existe.' });
    if (!(await checkPassword(body.current, rows[0].pass_hash))) { await sleep(600); return sendJson(res, 400, { error: 'La contraseña actual no es correcta.' }); }
    await db('PATCH', `clients?id=eq.${enc(auth.id)}`, { pass_hash: await hashPassword(body.next) }, 'return=minimal');
    return sendJson(res, 200, { ok: true });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo cambiar la contraseña' });
  }
};
