// Acceso a la base de datos compartida (Supabase Postgres vía REST) con la clave de servicio.
// La clave solo existe en el servidor (variable SUPABASE_SERVICE_KEY en Vercel).

function baseUrl() {
  return process.env.SUPABASE_URL || 'https://gvricpzxiumcaaecaqho.supabase.co';
}
function serviceKey() {
  const k = process.env.SUPABASE_SERVICE_KEY;
  if (!k) throw new Error('Falta SUPABASE_SERVICE_KEY en Vercel');
  return k;
}

async function db(method, path, body, prefer) {
  const k = serviceKey();
  const headers = { apikey: k, Authorization: 'Bearer ' + k, 'Content-Type': 'application/json' };
  if (prefer) headers.Prefer = prefer;
  const res = await fetch(baseUrl() + '/rest/v1/' + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
  if (!res.ok) {
    const err = new Error((data && (data.message || data.error)) || 'Error de base de datos');
    err.status = res.status;
    err.code = data && data.code;
    throw err;
  }
  return data;
}

const enc = encodeURIComponent;

module.exports = { db, enc };
