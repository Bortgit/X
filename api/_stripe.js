// Utilidades compartidas para hablar con Stripe sin SDK (solo fetch).
// El prefijo "_" hace que Vercel NO lo publique como endpoint.

const STRIPE_API = 'https://api.stripe.com/v1';

const ALLOWED_HOSTS = ['balanceddogclub.com', 'www.balanceddogclub.com'];

function secretKey() {
  const k = process.env.STRIPE_SECRET_KEY;
  if (!k) throw new Error('Falta STRIPE_SECRET_KEY en Vercel');
  return k;
}

// Convierte objetos/arrays anidados al formato de formulario de Stripe: a[b][0][c]=v
function encode(value, prefix, pairs) {
  pairs = pairs || [];
  if (value === undefined || value === null) return pairs;
  if (Array.isArray(value)) {
    value.forEach((v, i) => encode(v, `${prefix}[${i}]`, pairs));
  } else if (typeof value === 'object') {
    Object.keys(value).forEach((k) => encode(value[k], prefix ? `${prefix}[${k}]` : k, pairs));
  } else {
    pairs.push(encodeURIComponent(prefix) + '=' + encodeURIComponent(String(value)));
  }
  return pairs;
}

async function stripe(method, path, params) {
  const headers = { Authorization: 'Bearer ' + secretKey() };
  let url = STRIPE_API + path;
  const opts = { method, headers };
  if (params) {
    const body = encode(params, '').join('&');
    if (method === 'GET') {
      url += (url.includes('?') ? '&' : '?') + body;
    } else {
      opts.body = body;
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }
  }
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) {
    const err = new Error((data && data.error && data.error.message) || 'Error de Stripe');
    err.status = res.status;
    throw err;
  }
  return data;
}

// Dominio al que vuelve el cliente tras pagar. Solo dominios propios.
function originFor(req) {
  const host = String(req.headers['x-forwarded-host'] || req.headers.host || '')
    .split(',')[0]
    .trim()
    .toLowerCase();
  if (ALLOWED_HOSTS.includes(host) || host.endsWith('.vercel.app')) return 'https://' + host;
  return 'https://www.balanceddogclub.com';
}

function sendJson(res, status, obj) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(obj));
}

module.exports = { stripe, originFor, sendJson };
