// Un cliente cambia su propia contraseña.
//  - Normal: necesita la actual.
//  - Obligatorio (tras una contraseña temporal del admin): no pide la actual, pero la nueva debe ser distinta.

const { sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth, hashPassword, checkPassword, passwordProblem, sleep } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'client') return sendJson(res, 403, { error: 'Solo los clientes cambian su contraseña aquí' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    const bad = passwordProblem(body.next);
    if (bad) return sendJson(res, 400, { error: bad });
    const rows = await db('GET', `clients?select=pass_hash,must_change&id=eq.${enc(auth.id)}`);
    if (!rows.length) return sendJson(res, 401, { error: 'La cuenta ya no existe.' });
    if (body.forced) {
      if (!rows[0].must_change) return sendJson(res, 400, { error: 'No hay ningún cambio obligatorio pendiente.' });
      if (await checkPassword(body.next, rows[0].pass_hash)) return sendJson(res, 400, { error: 'Elige una contraseña distinta de la temporal.' });
    } else if (!(await checkPassword(body.current, rows[0].pass_hash))) {
      await sleep(600);
      return sendJson(res, 400, { error: 'La contraseña actual no es correcta.' });
    }
    await db('PATCH', `clients?id=eq.${enc(auth.id)}`, { pass_hash: await hashPassword(body.next), must_change: false }, 'return=minimal');
    return sendJson(res, 200, { ok: true });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo cambiar la contraseña' });
  }
};
