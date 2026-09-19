# Blackstories Bot

Bot que permite a los seguidores de un Instagram profesional jugar a
**Black Stories** (misterios de sí/no) por mensaje directo. Una IA arbitra
las preguntas; el juego se controla por completo editando un archivo de
texto (`blackstorie/blackstorie.txt`).

El bot **solo** responde a mensajes que empiecen por la palabra `reto` y
**solo** si hay una historia activa. Cualquier otro mensaje (por ejemplo,
clientes preguntando por servicios de adiestramiento canino) nunca recibe
respuesta automática.

## Requisitos

- Windows 10/11 (o cualquier SO con Python 3.11+).
- Python 3.11 o superior. Si no lo tienes instalado, descárgalo desde
  https://www.python.org/downloads/ y **marca la casilla "Add Python to
  PATH"** durante la instalación. Comprueba con `python --version` (o
  `py --version`) en una terminal.

## Instalación

### Paso 1: instalar Ollama (un solo doble-clic)

El bot usa Ollama en local por defecto: cero coste, cero tokens de pago,
cero configuración. Como no puedo instalar nada en tu PC desde esta
sesión (no tengo ningún acceso a tu ordenador), te dejo un script que lo
hace todo por ti con un solo doble-clic:

1. Abre la carpeta `scripts/` dentro de `blackstories-bot`.
2. Haz doble clic en **`instalar_ollama_windows.bat`**.
3. Espera a que termine (descarga Ollama, lo instala en silencio y
   descarga el modelo `llama3.1`; puede tardar varios minutos, son
   varios GB). Al final verás "Listo." en verde.

Si prefieres hacerlo tú mismo paso a paso, o el script falla por algún
motivo (por ejemplo, sin conexión a internet), la alternativa manual es:
instalar Ollama desde https://ollama.com/download y luego, en una
terminal, ejecutar `ollama pull llama3.1`.

### Paso 2: instalar el proyecto

Desde la carpeta del proyecto (`blackstories-bot`), en PowerShell o CMD:

```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**No hace falta tocar `.env` para nada** (el bot ya usa Ollama por
defecto sin configuración). Con eso, `python cli.py play` ya juega de
verdad.

Copia `.env.example` a `.env` únicamente si quieres cambiar algo (otro
modelo de Ollama, la API de Claude, límites, credenciales de Instagram,
etc.):

```
copy .env.example .env
```

## Uso en terminal

Cualquier punto de entrada (`cli.py`, `server.py`) crea automáticamente,
si no existen, la carpeta `blackstorie/` y dentro `blackstorie.txt`
(vacío) y `LEEME.txt` (con instrucciones). Nunca sobrescriben un archivo
que ya exista.

```
python cli.py status      # Muestra si hay historia activa
python cli.py play        # Modo interactivo: escribe mensajes "reto ..."
python cli.py send "reto ¿es un asesinato?"   # Un unico mensaje
```

`status` muestra:

```
JUGANDO: 812 caracteres (hash 3f9a1c2b7e4d...)
```

o bien:

```
SIN JUEGO: blackstorie.txt vacio, el bot no respondera.
```

### Cómo jugar

1. Abre `blackstorie/blackstorie.txt` con el Bloc de notas.
2. Pega tu historia. Formato recomendado (no obligatorio):

   ```
   ENIGMA: <lo que van a leer los jugadores>
   SOLUCION: <la explicación completa>
   ACLARACIONES (opcional): <notas tuyas para casos límite>
   ```

3. Guarda el archivo. El cambio se aplica al instante (el archivo se lee
   en cada mensaje, no hace falta reiniciar nada).
4. Para cambiar de historia, reemplaza el texto (esto reinicia el
   historial y los contadores de todos los jugadores para esa historia).
5. Para parar el juego, vacía el archivo por completo y guarda.

Todos los detalles están también en `blackstorie/LEEME.txt`, que se crea
solo la primera vez.

## Cómo cambiar de modelo de IA

En `.env`, variable `MODEL_PROVIDER` (si no existe el archivo `.env`, se
usa el valor por defecto igualmente, sin que tengas que crear nada):

- `ollama` (**por defecto**, sin tocar nada): usa un modelo local vía
  [Ollama](https://ollama.com/). Cero coste, cero tokens de pago, todo
  corre en tu PC. Configurable con `OLLAMA_HOST` (por defecto
  `http://localhost:11434`) y `OLLAMA_MODEL` (por defecto `llama3.1`).
  Requiere Ollama instalado, el modelo descargado (`ollama pull
  llama3.1`) y el servidor corriendo (`ollama serve`, o ya corre solo en
  Windows tras instalarlo).
- `claude`: usa la API de pago de Anthropic. Solo se activa si tú mismo
  cambias `MODEL_PROVIDER=claude` en `.env` y rellenas
  `ANTHROPIC_API_KEY`. Por defecto (`claude-haiku-4-5`) si decides
  usarla.
- `none`: desactiva la IA por completo (el bot solo responde a
  `ayuda`/`solución`/`me rindo`/bienvenida; cualquier pregunta real da
  el mensaje de "fallo técnico").

En ambos casos, la salida del modelo está **forzada** a una categoría
exacta (esquema JSON con enum en Ollama, tool use obligatorio con enum en
la API de Claude): el modelo nunca genera texto libre para el jugador.

## Cómo funciona blackstorie.txt (regla principal)

- El archivo vacío, o con solo espacios/saltos de línea/BOM, significa
  **sin juego**: el bot no responde absolutamente nada, ni siquiera a
  mensajes que empiecen por "reto". No cuenta para límites, no crea
  sesión de jugador. Solo deja una línea en el registro técnico.
- Se lee en cada mensaje entrante: no hace falta reiniciar el servidor
  para que un cambio surta efecto.
- Se admite UTF-8 (con o sin BOM) y, si falla, cp1252 (la codificación
  típica del Bloc de notas de Windows en español).
- Cada historia se identifica por el hash de su contenido (sin espacios
  al principio/final). Si el contenido cambia, es una historia nueva:
  se reinician el historial y los contadores de preguntas para todos.
- El bot **nunca** escribe en `blackstorie.txt`. Debe quedar vacío al
  terminar cualquier sesión de trabajo con el proyecto.

## Servidor y canal de Instagram

```
uvicorn server:app --host 0.0.0.0 --port 8000
```

Expone:

- `GET /webhook`: verificación del webhook de Meta (`hub.challenge`).
- `POST /webhook`: recibe eventos de mensajes, valida la firma
  `X-Hub-Signature-256` (si `IG_APP_SECRET` está configurado) y responde
  a través de la API de mensajería de Meta.
- `GET /health`: estado básico (si hay juego activo).

El canal (`channels/instagram.py`) no hace ninguna llamada real sin
credenciales: si `IG_PAGE_ACCESS_TOKEN` no está configurado, registra en
el log lo que habría enviado en vez de llamar a la API. Ver
`MANUAL_STEPS.md` para la configuración completa (cuenta de Instagram,
app en Meta for Developers, túnel/servidor, revisión de la app, etc.) y
las advertencias sobre qué no se pudo verificar contra la documentación
oficial de Meta desde este entorno.

## Batería de pruebas con el modelo real

Además de los tests unitarios (que nunca llaman a un modelo real), hay un
runner que evalúa la calidad de clasificación contra el modelo
configurado en `.env`:

```
python -m tests.run_battery --story tests/fixtures/story_1.txt --cases tests/fixtures/cases_1.json
```

- Si `MODEL_PROVIDER=none`, lo indica claramente y termina sin fallar.
- Si la historia (`--story`) está vacía, indica que no hay historia y
  termina sin fallar.
- Aprobado si hay **cero victorias falsas** y al menos **90%** de
  respuestas correctas.

Hay 3 historias de ejemplo ORIGINALES (marcadas como borrador, solo para
pruebas, no son Black Stories comerciales) en `tests/fixtures/story_1.txt`
a `story_3.txt`, cada una con ~20 casos en `cases_1.json` a `cases_3.json`.
**No copies estas historias de prueba a tu `blackstorie.txt` real.**

## Tests unitarios

```
pytest
```

Usan siempre rutas temporales (nunca tu `blackstorie.txt` real) y un
modelo simulado que lanza una excepción si se le llama, para demostrar
que el motor no llama a la IA cuando no debe (sin historia activa, en
los interceptores de código, con el interruptor de apagado activo, etc.).

## Estructura del proyecto

```
core/            nucleo del bot (independiente de cualquier canal)
  config.py      configuracion desde .env
  blackstorie.py regla principal: archivo blackstorie.txt
  db.py          SQLite: progreso por jugador, dedup, registro
  limits.py      limites de ritmo, tope de preguntas, apagado
  llm.py         abstraccion del modelo (Ollama / Claude / ninguno)
  personality.py plantillas de personalidad
  engine.py      handle_message(): el pipeline completo
channels/
  instagram.py   adaptador de Instagram (webhook, firma, envio)
prompts/
  arbiter.md         plantilla del arbitro (categoriza preguntas)
  guess_checker.md   plantilla del comprobador de soluciones
personality.yaml     ficha de personaje y mensajes
cli.py                canal de terminal
server.py             servidor FastAPI
tests/                pytest + fixtures + bateria con modelo real
```

## Notas del entorno de desarrollo

Este proyecto se generó en una sesión de Claude Code ejecutada en un
contenedor remoto (Linux), no en tu equipo Windows: no existía ya una
carpeta `blackstories-bot` en ese entorno, así que todo el código se creó
en la raíz del repositorio git que esa sesión tenía disponible. Copia o
clona este repositorio dentro de tu carpeta `blackstories-bot` en el
Escritorio para seguir trabajando localmente en Windows. Ver
`DECISIONS.md` para el resto de decisiones tomadas de forma autónoma.
