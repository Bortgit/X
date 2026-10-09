// Sesiones firmadas y contraseñas (todo en el servidor).

const crypto = require('crypto');
const { sendJson } = require('./_stripe');

const TOKEN_DAYS = 30;
// Hash SHA-256 de la contraseña de admin actual. Se puede sustituir poniendo
// ADMIN_PASSWORD_HASH (sha256 hex de la nueva contraseña) en Vercel.
const DEFAULT_ADMIN_HASH = 'b7813fab7536afc71b115a930379bf96b03ccea0193366c231b5635ca2a5480d';

function secret() {
  return crypto.createHash('sha256').update('bd-token:' + (process.env.SUPABASE_SERVICE_KEY || '')).digest();
}
const b64u = (buf) => Buffer.from(buf).toString('base64url');

function signToken(payload) {
  const body = b64u(JSON.stringify(Object.assign({ exp: Date.now() + TOKEN_DAYS * 86400000 }, payload)));
  const sig = crypto.createHmac('sha256', secret()).update(body).digest('base64url');
  return body + '.' + sig;
}

// Devuelve {role:'client'|'admin', id} o null.
function readToken(req) {
  const h = String(req.headers.authorization || '');
  const m = /^Bearer ([\w-]+)\.([\w-]+)$/.exec(h);
  if (!m) return null;
  const expected = crypto.createHmac('sha256', secret()).update(m[1]).digest();
  let given;
  try { given = Buffer.from(m[2], 'base64url'); } catch (e) { return null; }
  if (given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) return null;
  try {
    const p = JSON.parse(Buffer.from(m[1], 'base64url').toString('utf8'));
    if (!p.exp || p.exp < Date.now()) return null;
    return p.role === 'admin' ? { role: 'admin' } : p.role === 'client' && p.id ? { role: 'client', id: String(p.id) } : null;
  } catch (e) { return null; }
}

function requireAuth(req, res) {
  const t = readToken(req);
  if (!t) { sendJson(res, 401, { error: 'Sesión caducada. Vuelve a entrar.' }); return null; }
  return t;
}

function scryptAsync(pw, salt) {
  return new Promise((resolve, reject) => crypto.scrypt(pw, salt, 32, (e, k) => (e ? reject(e) : resolve(k))));
}
async function hashPassword(pw) {
  const salt = crypto.randomBytes(16);
  const key = await scryptAsync(String(pw), salt);
  return salt.toString('hex') + ':' + key.toString('hex');
}
async function checkPassword(pw, stored) {
  const [saltHex, keyHex] = String(stored || '').split(':');
  if (!saltHex || !keyHex) return false;
  const key = await scryptAsync(String(pw), Buffer.from(saltHex, 'hex'));
  const want = Buffer.from(keyHex, 'hex');
  return key.length === want.length && crypto.timingSafeEqual(key, want);
}
function adminPasswordOk(pw) {
  const want = (process.env.ADMIN_PASSWORD_HASH || DEFAULT_ADMIN_HASH).toLowerCase();
  const got = crypto.createHash('sha256').update(String(pw)).digest('hex');
  return got.length === want.length && crypto.timingSafeEqual(Buffer.from(got), Buffer.from(want));
}
const PASSWORD_RULES = 'La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número.';
// Devuelve null si la contraseña es válida, o el texto del problema.
function passwordProblem(pw) {
  const p = String(pw || '');
  return p.length >= 8 && /[a-z]/.test(p) && /[A-Z]/.test(p) && /\d/.test(p) ? null : PASSWORD_RULES;
}
const normPhone = (p) => String(p || '').replace(/\s+/g, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = { passwordProblem, signToken, readToken, requireAuth, hashPassword, checkPassword, adminPasswordOk, normPhone, sleep };
