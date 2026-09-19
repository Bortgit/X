# Borrador de política de privacidad — Bot de Black Stories en Instagram

> **Esto es un borrador de partida, no un documento legal.** Antes de
> publicarlo, revísalo (o pide que lo revise alguien con conocimientos
> legales) y adáptalo a tu situación real, tu país y la normativa que te
> aplique (en España/UE, el RGPD). Meta exige un enlace público a una
> política de privacidad para aprobar los permisos de mensajería de la
> app, así que este texto debe vivir en una URL accesible (una página de
> tu web, un documento público, etc.), no solo en este archivo.

## 1. Quién trata los datos

[Tu nombre o el de tu negocio de adiestramiento canino], como responsable
de la cuenta de Instagram y del bot conversacional asociado a ella.
Contacto: [tu email de contacto].

## 2. Qué datos se recogen

Cuando escribes al bot por mensaje directo de Instagram, se guarda:

- Tu identificador de usuario de Instagram (el que asigna Meta, no tu
  nombre real ni tu usuario público directamente).
- El contenido de los mensajes que envías al bot y las respuestas que
  recibes (**las conversaciones se guardan**), junto con la fecha y hora.
- El identificador de la historia que estabas jugando y tu progreso
  (número de preguntas realizadas, si ganaste o si te rendiste).

No se recoge ni se guarda información de pago, ni datos de contacto
distintos del identificador de Instagram, salvo que tú mismo los escribas
voluntariamente en un mensaje (en cuyo caso, evita compartir datos
sensibles por este canal).

## 3. Para qué se usan

- Hacer funcionar el juego (saber por qué historia vas, cuántas
  preguntas llevas, si has acertado).
- Evitar abusos: límites de mensajes por minuto, tope de preguntas por
  historia, detección de mensajes duplicados.
- Revisar manualmente las conversaciones para mejorar el juego y detectar
  problemas (respuestas incorrectas, fallos técnicos, intentos de manipular
  al bot).

No se usan para publicidad, no se venden ni se ceden a terceros, y no se
usan para tomar decisiones automatizadas que te afecten legalmente.

## 4. Dónde se guardan y durante cuánto tiempo

Los datos se guardan en una base de datos local (SQLite) del sistema que
opera el bot. [Completa aquí dónde corre ese sistema en producción: tu
propio servidor, un proveedor de hosting concreto, etc.]

[Define aquí un plazo de conservación razonable, por ejemplo: "Las
conversaciones se conservan durante un máximo de 12 meses desde el último
mensaje, tras lo cual se eliminan."]

## 5. Con quién se comparten

- Con **Meta/Instagram**, en la medida necesaria para poder enviarte los
  mensajes (es la plataforma sobre la que funciona el DM).
- [Si usas Ollama en local: "El contenido de tus mensajes se procesa
  localmente en el mismo servidor, sin enviarse a terceros para la parte
  de inteligencia artificial."]
- [Si usas la API de Claude: "El contenido de tus mensajes (la pregunta
  que escribes y el texto de la historia) se envía a Anthropic (la
  empresa que ofrece el modelo de IA Claude) para poder clasificar tu
  pregunta. Consulta la política de privacidad de Anthropic en
  https://www.anthropic.com/legal/privacy"]

## 6. Tus derechos

Puedes pedirnos en cualquier momento, escribiéndonos a [tu email de
contacto]:

- Saber qué datos tuyos tenemos guardados.
- Pedir que los borremos.
- Retirar tu consentimiento para seguir jugando (dejando de escribirnos,
  o pidiéndonos que eliminemos tu historial).

## 7. Menores de edad

[Decide y completa: por ejemplo, "Este juego no está dirigido a menores
de 14 años. Si detectamos que un usuario es menor de esa edad, eliminamos
su conversación."]

## 8. Cambios en esta política

Podemos actualizar este documento. Si lo hacemos, publicaremos la nueva
versión en el mismo enlace y actualizaremos la fecha de "última
actualización" abajo.

---

Última actualización: [fecha]
