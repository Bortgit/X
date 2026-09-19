# Lo que te toca hacer a ti (en orden)

El código y las pruebas ya están hechos. Esto es lo que solo tú puedes
decidir o ejecutar, en el orden en que tiene sentido hacerlo.

> **Aviso importante**: en el entorno donde se construyó este proyecto no
> se pudo acceder directamente a `developers.facebook.com` (el proxy de
> red de la sesión bloquea ese dominio), así que los detalles de Meta de
> más abajo (nombres de permisos, ventana de 24h, estructura del webhook)
> se verificaron por búsqueda web de fuentes que citan la documentación
> oficial vigente en 2026, no leyendo la página de Meta directamente.
> Meta cambia estos detalles con cierta frecuencia: antes de dar cada
> paso, confírmalo tú mismo en https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/

## 1. Cuenta profesional de Instagram

- Tu cuenta de Instagram debe ser una cuenta **profesional** (Business o
  Creator), no personal. Actívalo desde Ajustes → Cuenta → Cambiar a
  cuenta profesional.
- La mensajería de la API de Instagram funciona con **Instagram API con
  inicio de sesión de Instagram** (no hace falta vincular una Página de
  Facebook con el flujo más reciente, pero confírmalo para tu caso
  concreto en la documentación de Meta, porque hay variantes según cómo
  crees la app).

## 2. Decide la vía: herramienta intermedia vs API propia

Dos caminos posibles:

- **Herramienta intermedia (ej. ManyChat, ChatFuel)**: más rápido de
  poner en marcha, sin necesidad de mantener tú mismo un servidor con
  HTTPS público, pero menos control sobre la lógica del juego y sueles
  depender de sus límites/planes de pago.
- **API propia (lo que implementa este proyecto)**: más control (todo el
  motor de juego, límites, personalidad y base de datos son tuyos), pero
  tú te encargas de mantener un servidor accesible por HTTPS.

Como este proyecto ya implementa el canal de Instagram como servidor
propio (`server.py` + `channels/instagram.py`), la recomendación es
seguir con la **API propia**, salvo que prefieras evitarte la parte de
mantener un servidor: en ese caso, ManyChat sería la alternativa, pero
requeriría adaptar la lógica del juego a su editor de flujos (no a este
código).

## 3. Crea la app en Meta for Developers

1. Ve a https://developers.facebook.com/apps y crea una app nueva de tipo
   "Business".
2. Añade el producto **Instagram** (mensajería) a la app.
3. Conecta tu cuenta profesional de Instagram a la app.
4. Solicita (para pruebas, primero en modo desarrollo) los permisos:
   - `instagram_business_basic`
   - `instagram_business_manage_messages`
   (Verifica el nombre exacto y si hace falta algún permiso adicional en
   el momento de configurarlo: Meta los ha ido renombrando con las
   distintas versiones de la API.)
5. Con la app en modo desarrollo puedes probar el envío/recepción de
   mensajes contigo mismo y con usuarios que añadas como "testers" de la
   app, sin pasar aún por la revisión de Meta.

**Nota importante**: Meta expone una única API de mensajería ("Send
API") tanto para responder como para iniciar una conversación, así que
el permiso `instagram_business_manage_messages` es el mismo en ambos
casos. Pero este bot **nunca inicia conversaciones**: solo llama a esa
API justo después de recibir un mensaje del jugador
(`channels/instagram.py::send_message`, invocada únicamente dentro del
webhook de mensajes entrantes). Al ser 100% reactivo, siempre responde
dentro de la ventana de 24 horas desde el último mensaje del usuario, así
que no necesitas ninguna etiqueta especial de mensaje "fuera de ventana"
(esas son solo para quien envía mensajes sin que el usuario haya escrito
antes, como marketing o recordatorios). Esto también simplifica la
revisión de Meta: no es una herramienta de difusión, es un bot de
respuesta a mensajes recibidos.

## 4. Túnel o servidor para el webhook

Meta necesita una URL **HTTPS pública** para mandar los eventos de
mensajes:

- Para desarrollo/pruebas: usa [ngrok](https://ngrok.com/) (`ngrok http
  8000`) apuntando a tu servidor local (`uvicorn server:app --port 8000`).
- Para producción: despliega `server.py` en un servidor con HTTPS (un
  VPS con Nginx + certificado, o un proveedor tipo Railway/Render).

Configura en el panel de Meta (Webhooks → Instagram):

- **Callback URL**: `https://tu-dominio-o-tunel/webhook`
- **Verify token**: el mismo valor que pongas en `IG_VERIFY_TOKEN` de tu
  `.env`.
- Suscríbete al campo `messages` (y revisa si necesitas también
  `messaging_postbacks` u otros, según lo que ofrezca el panel en ese
  momento).

Copia también el **App Secret** de tu app en `IG_APP_SECRET` (se usa para
validar la firma `X-Hub-Signature-256` de cada evento) y el **Page/User
Access Token** de mensajería en `IG_PAGE_ACCESS_TOKEN`.

## 5. Pega tu primera historia y pruébala con la batería

1. Arranca cualquier punto de entrada una vez (`python cli.py status`)
   para que se cree `blackstorie/blackstorie.txt` y `LEEME.txt`.
2. Pega tu historia (con su solución) en `blackstorie/blackstorie.txt`.
3. Comprueba con `python cli.py status` que dice "JUGANDO".
4. Juega un rato en terminal con `python cli.py play` para revisar que
   las respuestas tienen sentido.
5. Si quieres medir la calidad del modelo de forma más sistemática,
   copia tu historia a un archivo de pruebas (fuera de
   `blackstorie/blackstorie.txt`) y crea un archivo de casos como los de
   `tests/fixtures/cases_1.json`, y ejecuta:
   ```
   python -m tests.run_battery --story tu_historia.txt --cases tus_casos.json
   ```

## 6. Revisa el tono

Abre `personality.yaml` y lee las variantes y los mensajes fijos. Ajusta
el tono si "misterioso y oscuro" no encaja con lo que quieres transmitir
a tus seguidores, manteniendo la regla de que todas las variantes de una
misma categoría dicen exactamente lo mismo (solo cambia el estilo).

## 7. Política de privacidad

Hay un borrador en `PRIVACY_DRAFT.md`. Complétalo (nombre del negocio,
email de contacto, plazos de conservación, si usas la API de Claude o
Ollama en local) y publícalo en una URL pública (una página de tu web,
por ejemplo). Meta pide ese enlace para aprobar los permisos de
mensajería.

## 8. Vídeo y envío a revisión de Meta

Para pasar de modo desarrollo a que cualquiera pueda escribirte y reciba
respuesta (el bot solo responde a quien te escribe primero, nunca
escribe él primero a nadie):

1. Graba un vídeo de pantalla mostrando el flujo completo: un usuario
   escribiendo "reto ..." por Instagram y el bot respondiendo.
2. En el panel de la app, ve a **App Review** y solicita el permiso
   `instagram_business_manage_messages` (Advanced Access), adjuntando el
   vídeo, el enlace a tu política de privacidad y una descripción clara
   de para qué usas la mensajería (el juego de Black Stories, solo en
   modo respuesta, nunca envíos no solicitados).
3. Espera la revisión de Meta (puede tardar varios días).

## 9. Beta cerrada con 5-10 testers

Antes o durante la revisión, añade entre 5 y 10 personas de confianza
como **testers de Instagram** en el panel de la app (esto les permite
usar el bot en modo desarrollo, antes de que Meta apruebe el permiso
avanzado). Pídeles que jueguen una historia completa y que te avisen de
cualquier respuesta rara, mensaje repetido, o comportamiento inesperado
(por ejemplo, que el bot responda a algo que no empieza por "reto", cosa
que no debería pasar nunca: avísame si ves eso).

## 10. Lanzamiento

Una vez aprobado el permiso avanzado:

1. Cambia la app a modo "Live" en el panel de Meta.
2. Despliega `server.py` en tu servidor definitivo (con HTTPS real, no
   un túnel de pruebas).
3. Configura `BOT_SHUTDOWN=0` (o borra el archivo `SHUTDOWN` si existe)
   para asegurarte de que el interruptor de apagado no está activo.
4. Pega tu primera historia real en `blackstorie/blackstorie.txt` y
   anuncia el juego a tus seguidores.
5. Revisa de vez en cuando el registro (`interaction_log` en la base de
   datos SQLite) para ver cómo está jugando la gente y detectar
   respuestas que quieras mejorar.
