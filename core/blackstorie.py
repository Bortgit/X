"""Gestion del archivo blackstorie.txt: la REGLA PRINCIPAL del proyecto.

- Crea automaticamente la carpeta y el archivo (vacio) si no existen.
- Nunca sobrescribe un archivo que ya exista.
- Lee en cada llamada (sin cache de proceso) para reflejar cambios al instante.
- Tolera UTF-8 con BOM y cae a cp1252 si falla la decodificacion.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from core.config import Settings, settings as default_settings

logger = logging.getLogger("blackstories.blackstorie")

LEEME_CONTENTS = """LEEME - Como controlar el juego de Black Stories
==================================================

Este archivo (LEEME.txt) es solo para ti. Las instrucciones para el bot
estan aqui; el archivo "blackstorie.txt" que esta a su lado debe contener
UNICAMENTE el texto de la historia que quieres que se juegue ahora mismo.

QUE PEGAR EN blackstorie.txt
-----------------------------
Pega ahi, como texto libre, el enigma y su solucion. Formato recomendado
(no obligatorio):

    ENIGMA: <el planteamiento que van a leer los jugadores>
    SOLUCION: <la explicacion completa de lo que ocurrio de verdad>
    ACLARACIONES (opcional): <notas tuyas para resolver dudas o casos
    limite, por ejemplo "el arma SI cuenta como relevante">

Tambien puedes pegar el texto sin etiquetas. En ese caso, el bot
entendera que el primer parrafo (el planteamiento) es lo que ven los
jugadores, y el resto es la solucion secreta. Cualquier aclaracion o
nota que añadas prevalece siempre sobre el criterio propio de la IA.

REGLAS IMPORTANTES
-------------------
1. Archivo VACIO (o solo con espacios/saltos de linea) = SIN JUEGO.
   El bot no respondera a nadie, ni siquiera a mensajes que empiecen
   por "reto". Esos mensajes te llegaran a ti como cualquier otro DM.

2. Para EMPEZAR una partida: pega la historia completa en
   blackstorie.txt y guarda el archivo. El cambio se aplica al
   instante, sin reiniciar nada.

3. Para CAMBIAR de historia: borra el contenido anterior y pega el
   nuevo. Al cambiar el texto, se reinician automaticamente el
   historial y los contadores de preguntas de TODOS los jugadores
   (es una historia nueva).

4. Para PARAR el juego: vacia el archivo (borra todo el contenido y
   guarda). El bot dejara de responder de inmediato.

5. El bot NUNCA escribe nada dentro de blackstorie.txt. Ese archivo
   es solo tuyo.

Guarda el archivo en UTF-8 si puedes (el Bloc de notas de Windows
tambien funciona: el bot detecta y tolera ese formato).
"""


@dataclass(frozen=True)
class StoryState:
    """Resultado de leer blackstorie.txt en un instante dado."""

    raw_text: str
    normalized_text: str
    is_active: bool
    story_hash: str | None
    char_count: int
    encoding_used: str


def ensure_blackstorie_files(cfg: Settings | None = None) -> None:
    """Crea la carpeta y los archivos si no existen. Nunca toca los existentes."""
    cfg = cfg or default_settings
    directory = cfg.blackstorie_dir
    directory.mkdir(parents=True, exist_ok=True)

    story_file = cfg.blackstorie_file
    if not story_file.exists():
        story_file.write_bytes(b"")
        logger.info("Creado %s vacio", story_file)

    readme_file = cfg.blackstorie_readme
    if not readme_file.exists():
        readme_file.write_text(LEEME_CONTENTS, encoding="utf-8")
        logger.info("Creado %s", readme_file)


def decode_bytes(raw_bytes: bytes) -> tuple[str, str]:
    """Decodifica tolerando BOM UTF-8 y, si falla, cp1252. Devuelve (texto, encoding)."""
    try:
        return raw_bytes.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw_bytes.decode("cp1252"), "cp1252"


_decode = decode_bytes  # alias interno


def read_story(cfg: Settings | None = None) -> StoryState:
    """Lee blackstorie.txt tal cual esta AHORA (sin cache)."""
    cfg = cfg or default_settings
    ensure_blackstorie_files(cfg)

    raw_bytes = cfg.blackstorie_file.read_bytes()
    text, encoding_used = _decode(raw_bytes)

    normalized = text.strip()
    is_active = len(normalized) > 0

    story_hash = None
    if is_active:
        story_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if len(normalized) > cfg.max_story_chars:
            logger.warning(
                "blackstorie.txt supera %s caracteres (%s); se usara igualmente",
                cfg.max_story_chars,
                len(normalized),
            )

    return StoryState(
        raw_text=text,
        normalized_text=normalized,
        is_active=is_active,
        story_hash=story_hash,
        char_count=len(normalized),
        encoding_used=encoding_used,
    )
