# Pendientes para cuando se construya la app real (con backend)

Este prototipo es solo HTML/JS + localStorage, sin servidor, así que lo de
aquí abajo no se puede implementar de verdad todavía — queda anotado para
no perderlo cuando llegue el momento de construir la app con backend real.

## Notificación push diaria a las 9:00

- Tarea programada (cron) a las 9:00 cada día.
- Revisa las reservas del día (adiestramiento/videollamada, residencia) por cliente.
- Si el cliente NO tiene nada reservado ese día → no se le envía nada.
- Si el cliente SÍ tiene algo reservado ese día → notificación push a su móvil
  con el detalle (qué tiene y a qué hora).
- Al admin (adiestrador) → notificación push con el resumen de TODAS las
  sesiones reservadas ese día por todos los clientes (si no hay ninguna, no
  se le envía nada).
- Requiere: backend con cron + servicio de push real (Firebase/APNs para app
  nativa, o Web Push si es web) o WhatsApp Business API si se prefiere por WhatsApp.

## Vista de calendario/agenda (cliente y admin)

- Idea: una sección simple de calendario donde de un vistazo se vea qué hay
  reservado y para cuándo, sin depender de esperar la notificación del día.
- Cliente: solo sus propias reservas (dato ya existe en
  `bookingsTraining` / `bookingsResidencia` del cliente).
- Admin: agregación de las reservas de TODOS los clientes por día (más curro
  que la vista de cliente, pero factible con los datos que ya hay).
- Decisión: valorada positivamente, pendiente de implementar cuando se
  retome el prototipo.
