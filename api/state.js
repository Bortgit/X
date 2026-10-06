// Devuelve los datos compartidos según quién pregunta.
//  - cliente: su propia ficha completa + las reservas (anónimas) de los demás, solo para ocupación.
//  - admin: todas las fichas.
// Con ?stamp=XXXX responde {unchanged:true} si no ha cambiado nada (sondeo barato).

const crypto = require('crypto');
const { db, enc } = require('./_db');
const { sendJson } = require('./_stripe');
const { requireAuth } = require('./_auth');

function shadowOf(row) {
  const d = row.data || {};
  const strip = (arr) => (Array.isArray(arr) ? arr : []).map((b) => { const x = Object.assign({}, b); delete x.paidAmount; return x; });
  return {
    id: row.id, rev: row.rev,
    data: {
      id: row.id, _shadow: true,
      bookingsTraining: strip(d.bookingsTraining),
      bookingsResidencia: strip(d.bookingsResidencia),
      bookingsGuarderia: strip(d.bookingsGuarderia),
    },
  };
}

module.exports = async (req, res) => {
  if (req.method !== 'GET') return sendJson(res, 405, { error: 'Método no permitido' });
  const auth = requireAuth(req, res);
  if (!auth) return;
  try {
    const url = new URL(req.url, 'https://x.invalid');
    const since = url.searchParams.get('stamp');

    const [revs, setRevs] = await Promise.all([
      db('GET', 'clients?select=id,rev&order=id'),
      db('GET', 'app_settings?select=key,rev&order=key'),
    ]);
    if (auth.role === 'client' && !revs.some((r) => r.id === auth.id)) return sendJson(res, 401, { error: 'La cuenta ya no existe.' });
    const stamp = crypto.createHash('sha1')
      .update(revs.map((r) => r.id + ':' + r.rev).join(',') + '|' + setRevs.map((r) => r.key + ':' + r.rev).join(','))
      .digest('hex').slice(0, 16);
    if (since && since === stamp) return sendJson(res, 200, { unchanged: true, stamp });

    const [rows, settingRows] = await Promise.all([
      db('GET', 'clients?select=id,rev,data&order=id'),
      db('GET', 'app_settings?select=key,rev,value'),
    ]);
    const settings = {};
    settingRows.forEach((s) => { settings[s.key] = { rev: s.rev, value: s.value }; });

    let clients;
    if (auth.role === 'admin') clients = rows.map((r) => ({ id: r.id, rev: r.rev, data: r.data }));
    else clients = rows.map((r) => (r.id === auth.id ? { id: r.id, rev: r.rev, data: r.data } : shadowOf(r)));

    return sendJson(res, 200, { stamp, role: auth.role, clients, settings });
  } catch (e) {
    return sendJson(res, 500, { error: e.message || 'No se pudo leer el estado' });
  }
};
