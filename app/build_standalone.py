# -*- coding: utf-8 -*-
"""Genera la versión independiente (PWA) de Bilbo Coach a partir de bilbo-app.html.

La lógica de entrenamiento es la misma; solo cambia el almacenamiento (datos en el
propio dispositivo, sin claude.ai), las copias de seguridad y el modo app (manifest,
service worker para uso sin conexión e iconos).

Uso: python3 app/build_standalone.py  -> escribe app/standalone/
"""
import os, re, struct, zlib, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "bilbo-app.html")
OUT = os.path.join(HERE, "standalone")
os.makedirs(OUT, exist_ok=True)
src = open(SRC, encoding="utf-8").read()


def rep(s, a, b):
    assert a in s, "no encontrado: " + a[:90]
    return s.replace(a, b, 1)


# ---------------- almacenamiento local en lugar de la base de datos de claude.ai
s = src
s = rep(s, '''async function writeSession(s){
  const {id,...body}=s;
  if(!db){s.pending=true;LS.set("bilbo.sessions",sessions);return}
  try{await db.doc("sesiones/"+id).set(body);delete s.pending}
  catch(e){s.pending=true;toast("No se pudo guardar en la nube; queda en este dispositivo.")}
  LS.set("bilbo.sessions",sessions);
}''', '''async function writeSession(s){delete s.pending;LS.set("bilbo.sessions",sessions)}''')
s = re.sub(r'function cfgChanged\(\)\{.*?\n', 'function cfgChanged(){LS.set("bilbo.cfg",cfg)}\n', s, count=1)
s = rep(s, '''      if(db){try{await db.doc("sesiones/"+id).delete()}catch(_){toast("No se pudo eliminar en la nube.")}}render();''', '''      render();''')
s = re.sub(r'async function download\(name,data\)\{.*?\n\}\n', '''async function download(name,data){
  const type=name.endsWith(".csv")?"text/csv":"application/json";
  try{const f=new File([data],name,{type});
    if(navigator.canShare&&navigator.canShare({files:[f]})){await navigator.share({files:[f],title:name});markBackup();return}}
  catch(e){if(e&&e.name==="AbortError")return}
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([data],{type}));a.download=name;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},1000);markBackup();
}
function markBackup(){LS.set("bilbo.lastBackup",Date.now());toast("Copia lista. Guárdala en Archivos o iCloud.")}
''', s, count=1, flags=re.S)
s = re.sub(r'function dbBanner\(\)\{.*?\n\}\nasync function initCloud\(\)\{.*?\n\}\n', '''function dbBanner(){
  if(!sessions.length)return "";
  const lb=LS.get("bilbo.lastBackup",0),days=Math.floor((Date.now()-lb)/864e5);
  if(lb&&days<7)return "";
  return `<div class="banner warn">Tus datos viven en este iPhone. ${lb?`Tu última copia es de hace ${days} días.`:"Aún no has hecho ninguna copia."} <button class="btn small" id="exp-json">Hacer copia ahora</button></div>`;
}
async function initCloud(){
  try{if(navigator.storage&&navigator.storage.persist)await navigator.storage.persist()}catch(e){}
  if("serviceWorker" in navigator){try{await navigator.serviceWorker.register("./sw.js")}catch(e){}}
}
''', s, count=1, flags=re.S)
s = rep(s, 'let cfg=structuredClone(DEFAULT_CFG), sessions=[], db=null, dl=null, dbState="conectando";',
        'let cfg=structuredClone(DEFAULT_CFG), sessions=[], dbState="ok";')
s = rep(s, '''<p class="small muted">Los datos se guardan en la base de datos de esta app. Exporta de vez en cuando: el CSV sigue el formato de la hoja HISTORIAL del Excel.</p>''',
        '''<p class="small muted">Tus datos se guardan en este iPhone (no en internet). Haz una copia cada semana y guárdala en Archivos o iCloud: si borras la app o cambias de teléfono, «Importar copia» lo recupera todo. El CSV sigue el formato de la hoja HISTORIAL del Excel.</p>''')
assert "db." not in re.sub(r"//.*", "", s.split("<script>")[1]), "quedan llamadas a db"

# ---------------- documento completo con modo app
head = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Bilbo">
<meta name="theme-color" content="#12161B">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" href="icon-192.png">
<style>[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px)}body{margin:0}</style>
'''
body = s
body = body.replace("<title>Bilbo Coach</title>\n", "<title>Bilbo Coach</title>\n", 1)
i = body.index('<div class="wrap" id="app">')
html = head + body[:i] + "</head>\n<body>\n" + body[i:] + "\n</body>\n</html>\n"
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

# ---------------- manifest
open(os.path.join(OUT, "manifest.webmanifest"), "w", encoding="utf-8").write('''{
  "name": "Bilbo Coach",
  "short_name": "Bilbo",
  "lang": "es",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#0D1014",
  "theme_color": "#12161B",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
''')

# ---------------- service worker (sin conexión; la versión nueva llega al abrir la app)
ver = hashlib.sha1(html.encode()).hexdigest()[:10]
open(os.path.join(OUT, "sw.js"), "w", encoding="utf-8").write('''const V="bilbo-%s";
const SHELL=["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png","./apple-touch-icon.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const r=e.request;if(r.method!=="GET")return;
  const u=new URL(r.url);
  if(u.origin===location.origin&&r.mode==="navigate"){
    // red primero (para recibir actualizaciones), caché si no hay conexión
    e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put("./index.html",cp));return res}).catch(()=>caches.match("./index.html")));
    return;
  }
  if(u.origin===location.origin||u.host.endsWith("fonts.googleapis.com")||u.host.endsWith("fonts.gstatic.com")){
    e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put(r,cp));return res})));
  }
});
''' % ver)


# ---------------- iconos (PNG sin dependencias): barra con discos
def png(path, n):
    bg, bar, red, blue, white = (18, 22, 27), (200, 205, 212), (214, 40, 57), (27, 77, 219), (240, 242, 245)
    px = [[bg] * n for _ in range(n)]

    def rect(x0, y0, x1, y1, c):
        for y in range(int(y0 * n), int(y1 * n)):
            for x in range(int(x0 * n), int(x1 * n)):
                px[y][x] = c
    rect(.10, .47, .90, .53, bar)                    # barra
    rect(.20, .25, .29, .75, red); rect(.71, .25, .80, .75, red)      # discos grandes
    rect(.30, .33, .36, .67, blue); rect(.64, .33, .70, .67, blue)    # discos medianos
    rect(.37, .40, .40, .60, white); rect(.60, .40, .63, .60, white)  # topes
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in px)
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(os.path.join(OUT, path), "wb").write(data)


png("icon-192.png", 192)
png("icon-512.png", 512)
png("apple-touch-icon.png", 180)
print("OK ->", OUT, "versión", ver)
