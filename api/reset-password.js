// El admin genera una contraseña temporal para un cliente que la ha olvidado.
// Se devuelve una sola vez; en el servidor solo queda su versión cifrada.

const crypto = require('crypto');
const { sendJson } = require('./_stripe');
const { db, enc } = require('./_db');
const { requireAuth, hashPassword } = require('./_auth');

const ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'; // sin letras que se confunden (i, l, o, 0, 1)

function tempPassword() {
  let s = '';
  for (let i = 0; i < 8; i++) s += ALPHABET[crypto.randomInt(ALPHABET.length)];
  return s;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  if (auth.role !== 'admin') return sendJson(res, 403, { error: 'Solo el administrador puede restablecer contraseñas' });
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    const id = String(body.id || '');
    if (!id) return sendJson(res, 400, { error: 'Falta la cuenta' });
    const password = tempPassword();
    const upd = await db('PATCH', `clients?id=eq.${enc(id)}`, { pass_hash: await hashPassword(password) }, 'return=representation');
    if (!upd || !upd.length) return sendJson(res, 404, { error: 'La cuenta no existe' });
    return sendJson(res, 200, { ok: true, password });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo restablecer la contraseña' });
  }
};
