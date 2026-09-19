# Decisiones tomadas de forma autónoma

Este documento recoge las decisiones de diseño que tomé por mi cuenta
porque las instrucciones no las cerraban del todo, junto con el motivo.
Actué con criterio y seguí adelante, tal y como se me pidió.

## Entorno de trabajo

- La sesión de Claude Code en la que se construyó este proyecto se
  ejecuta en un contenedor remoto (Linux) atado a un repositorio git
  (`bortgit/x`), **no** en tu equipo Windows. No existía ninguna carpeta
  `blackstories-bot` en el Escritorio de ese entorno porque ese entorno
  no tiene Escritorio ni acceso al sistema de archivos de tu PC. Decisión:
  construir todo el proyecto en la raíz del repositorio (que hace de raíz
  de `blackstories-bot`) y dejarlo commiteado en la rama de trabajo. Debes
  clonar o copiar el contenido de esa rama a tu carpeta real en Windows
  para seguir trabajando localmente. Esto se avisa también en el README.

## Regla principal (blackstorie.txt)

- **`blackstorie/` se ignora en git** (`.gitignore`): la carpeta y el
  archivo vacío se recrean automáticamente en cualquier máquina al
  arrancar `cli.py` o `server.py`, así que no hace falta versionarlos, y
  así nunca se corre el riesgo de subir por accidente una historia real
  con su solución a un repositorio.
- **Aviso por superar 20.000 caracteres**: se registra un aviso en el log
  pero el archivo se usa igualmente (tal y como pedían las instrucciones),
  sin truncar el texto.

## Interceptores de código y mensajes fijos

- Las instrucciones piden que el código intercepte sin IA exactamente:
  `solución`/`solucion`, `me rindo` y `ayuda`. Añadí dos casos más,
  necesarios para que el flujo tenga sentido y que también se resuelven
  sin llamar a la IA:
  - **`reto` sin nada más** (o solo espacios) se interpreta como petición
    de **bienvenida** (mensaje de bienvenida/instrucciones iniciales).
  - Cualquier mensaje que, tras quitar "reto", quede vacío, se trata
    igual que el caso anterior.
- **"solución" y "me rindo" comparten el mismo mensaje fijo** (`me_rindo`
  en `personality.yaml`). Las instrucciones piden exactamente 6 mensajes
  fijos (bienvenida, ayuda, victoria, tope de preguntas, me rindo, fallo
  técnico) y especifican explícitamente que ni "solución" ni "me rindo"
  deben revelar nada: ambas acciones tienen la misma semántica de cara al
  jugador (abandonar sin conocer la respuesta), así que reutilizan el
  mismo mensaje en vez de inventar un séptimo tipo fuera de la lista
  pedida.
- **Categoría adicional "intento_fallido"**: el árbitro puede devolver
  `intento_solucion`, y el comprobador puede decidir que NO es una
  victoria completa. Las instrucciones no numeran una plantilla para ese
  caso concreto dentro de los 6 mensajes fijos. Silenciar al jugador ahí
  rompería el juego (dejaría sin respuesta a un intento de solución
  incorrecto), así que añadí un quinto grupo de variantes en
  `personality.yaml` (`intento_fallido`, con la misma cantidad de
  variantes y el mismo cuidado de no revelar nada ni sonar cercano) para
  cubrir ese caso sin salirme del criterio "la IA nunca escribe texto
  libre; todo sale de plantillas fijas".
- Si el jugador sigue preguntando después de ganar, se le vuelve a
  mostrar el mensaje de victoria (no hay una plantilla específica de
  "ya has ganado" en las instrucciones).
- "reto me rindo" marca `gave_up=1` en la base de datos para ese jugador
  y esa historia, pero **no bloquea** que siga jugando después: solo yo
  (vaciando/cambiando el archivo) termino una partida. Las instrucciones
  no piden bloquear al jugador tras rendirse.

## Orden de comprobaciones y qué cuenta como "pregunta"

- El tope de preguntas por historia se comprueba **antes** de saber si el
  mensaje es una pregunta real o un intercept de código (ayuda, solución,
  etc.), tal y como indica el orden explícito del enunciado (paso 5 antes
  que el paso 6). Un jugador que ya agotó el tope recibe siempre el
  mensaje de tope, incluso si escribe "reto ayuda".
- Solo cuentan para el tope de preguntas los mensajes que llegan a
  **llamar al árbitro** (o al comprobador, en el caso de un intento de
  solución). Los interceptores de código (bienvenida, ayuda, solicitud de
  solución, me rindo) **no** consumen preguntas del tope, porque no son
  preguntas de juego.
- Un fallo técnico del modelo en la llamada al árbitro **no** consume una
  pregunta del tope (no es responsabilidad del jugador que la IA falle).
  Si el fallo ocurre en la segunda llamada (comprobador, tras un
  `intento_solucion` ya clasificado), la pregunta ya se contó al obtener
  la clasificación, y así se queda.
- **Límite de ritmo por minuto y límite diario global superados**: el bot
  no responde nada (`None`), igual que con la regla principal de "sin
  historia". No hay una plantilla específica para esto en las
  instrucciones, y avisar "estás enviando mensajes muy rápido" desde una
  cuenta de Instagram sin contexto de juego podría resultar confuso o
  parecer spam del propio bot; se registra igualmente en el log técnico
  y en `interaction_log` para que puedas revisarlo.

## Deduplicado de mensajes

- Se usa `message_id` como clave única global (no por usuario), porque
  los `mid` que asigna Meta son únicos globalmente. Un mensaje con
  `message_id` repetido se ignora igual que si fuera un reenvío de Meta,
  independientemente de qué usuario lo mande.

## Historial al cambiar de historia

- Cambiar el contenido de `blackstorie.txt` no borra filas antiguas de la
  base de datos: como el progreso se guarda por `(user_id, story_hash)`,
  una historia nueva genera automáticamente una fila nueva con contador a
  cero. El historial de historias anteriores queda conservado para que
  puedas revisarlo, en vez de eliminarse.

## Modelo de IA

- Con `MODEL_PROVIDER=none` (valor por defecto de `.env.example`), el
  bot funciona igualmente para los interceptores de código (bienvenida,
  ayuda, solución, me rindo), pero cualquier pregunta real devuelve el
  mensaje de "fallo técnico", porque no hay ningún modelo que la
  clasifique. Esto permite instalar y probar el proyecto sin credenciales
  de ningún proveedor de IA antes de decidir cuál usar.

## Canal de Instagram

- No se pudo verificar en vivo la documentación de
  `developers.facebook.com` desde este entorno (el acceso a ese dominio
  está bloqueado por el proxy de red de la sesión). La información sobre
  permisos (`instagram_business_basic`,
  `instagram_business_manage_messages`), la ventana de 24 horas para
  responder y la forma del payload del webhook se obtuvo por búsqueda web
  de fuentes que citan la documentación oficial vigente en 2026, no
  leyendo directamente la página de Meta. Debes volver a verificarlo tú
  mismo contra `developers.facebook.com` en el momento de configurar la
  app real, porque Meta cambia estos detalles con cierta frecuencia. Ver
  `MANUAL_STEPS.md` para el detalle de lo que sí y no se pudo confirmar.
