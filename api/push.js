// Guarda cambios. Control de versiones por registro (rev): si alguien más lo cambió
// antes, devuelve conflict con la versión actual para que la app fusione y reintente.
//  - cliente: solo puede escribir SU ficha.
//  - admin: cualquier ficha y los ajustes globales (aforo, calendario, lectura, extras).

const { db, enc } = require('./_db');
const { sendJson } = require('./_stripe');
const { requireAuth } = require('./_auth');
const { guardClient, loadContext } = require('./_guard');

const SETTING_KEYS = ['admin', 'reading', 'extra'];

function clean(data, id) {
  const d = Object.assign({}, data || {});
  delete d.passwordSalt; delete d.passwordHash; delete d._shadow; delete d._audit;
  d.id = id;
  return d;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body || {};
    const results = [];

    for (const c of Array.isArray(body.clients) ? body.clients : []) {
      const id = String(c.id || '');
      if (auth.role === 'client' && id !== auth.id) { results.push({ id, error: 'forbidden' }); continue; }
      const rev = Number(c.rev);
      if (!Number.isInteger(rev) || rev < 1) { results.push({ id, error: 'bad rev' }); continue; }
      let data = clean(c.data, id);
      let patch = { rev: rev + 1, updated_at: new Date().toISOString() };
      let corrected = false;
      if (auth.role === 'client') {
        // El servidor comprueba que lo guardado es posible (XP, hucha, suscripción) antes de aceptarlo.
        const rows = await db('GET', `clients?select=rev,data,guard&id=eq.${enc(id)}`);
        if (!rows.length) { results.push({ id, error: 'missing' }); continue; }
        if (rows[0].rev === rev) {
          const g = guardClient(rows[0].data || {}, data, rows[0].guard, await loadContext(id));
          data = g.data; patch.guard = g.guard; corrected = g.corrected;
        }
      }
      patch.data = data;
      const upd = await db('PATCH', `clients?id=eq.${enc(id)}&rev=eq.${rev}`, patch, 'return=representation');
      if (upd && upd.length) { results.push(corrected ? { id, ok: true, rev: upd[0].rev, corrected: true, data: upd[0].data } : { id, ok: true, rev: upd[0].rev }); continue; }
      const cur = await db('GET', `clients?select=id,rev,data&id=eq.${enc(id)}`);
      results.push(cur.length ? { id, conflict: true, current: { rev: cur[0].rev, data: cur[0].data } } : { id, error: 'missing' });
    }

    for (const s of Array.isArray(body.settings) ? body.settings : []) {
      const key = String(s.key || '');
      if (auth.role !== 'admin' || !SETTING_KEYS.includes(key)) { results.push({ key, error: 'forbidden' }); continue; }
      const rev = Number(s.rev) || 0;
      let out = null;
      if (rev === 0) {
        try {
          const ins = await db('POST', 'app_settings', [{ key, value: s.value, rev: 1 }], 'return=representation');
          out = { key, ok: true, rev: ins[0].rev };
        } catch (e) { if (e.code !== '23505') throw e; }
      } else {
        const upd = await db('PATCH', `app_settings?key=eq.${enc(key)}&rev=eq.${rev}`,
          { value: s.value, rev: rev + 1, updated_at: new Date().toISOString() }, 'return=representation');
        if (upd && upd.length) out = { key, ok: true, rev: upd[0].rev };
      }
      if (!out) {
        const cur = await db('GET', `app_settings?select=key,rev,value&key=eq.${enc(key)}`);
        out = { key, conflict: true, current: cur.length ? { rev: cur[0].rev, value: cur[0].value } : { rev: 0, value: null } };
      }
      results.push(out);
    }

    return sendJson(res, 200, { results });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo guardar' });
  }
};
