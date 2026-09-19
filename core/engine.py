"""Nucleo del juego, independiente de cualquier canal (terminal, Instagram...).

`handle_message(user_id, message_id, text)` es el unico punto de entrada.
Devuelve el texto a enviar al jugador, o None si el bot no debe responder
nada (incluye el caso de que no haya historia activa).
"""
from __future__ import annotations

import logging
import re
import sqlite3
import unicodedata
from dataclasses import dataclass

from core import blackstorie, db, limits, personality as personality_mod
from core.config import Settings, settings as default_settings
from core.llm import BaseModel, GuessCheckResult, ModelError, build_model

logger = logging.getLogger("blackstories.engine")

_RETO_RE = re.compile(r"^\s*reto\b[\s:,\-]*", re.IGNORECASE)


def _normalize_keyword(text: str) -> str:
    text = text.strip().lower()
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_SOLUTION_KEYWORDS = {"solucion", "quiero la solucion", "dame la solucion", "dime la solucion"}
_GIVE_UP_KEYWORDS = {"me rindo", "rendirse", "me doy por vencido"}
_HELP_KEYWORDS = {"ayuda", "help", "reglas", "como se juega", "instrucciones"}


@dataclass(frozen=True)
class _Dependencies:
    cfg: Settings
    model: BaseModel
    conn: sqlite3.Connection


def _resolve_deps(
    cfg: Settings | None, model: BaseModel | None, conn: sqlite3.Connection | None
) -> _Dependencies:
    cfg = cfg or default_settings
    model = model if model is not None else build_model(cfg)
    conn = conn if conn is not None else db.get_connection(cfg)
    return _Dependencies(cfg=cfg, model=model, conn=conn)


def handle_message(
    user_id: str,
    message_id: str | None,
    text: str,
    *,
    cfg: Settings | None = None,
    model: BaseModel | None = None,
    conn: sqlite3.Connection | None = None,
    personality: personality_mod.Personality | None = None,
) -> str | None:
    """Procesa un mensaje entrante y devuelve la respuesta, o None si calla."""
    deps = _resolve_deps(cfg, model, conn)
    perso = personality or personality_mod.load_personality(deps.cfg)

    # 1. Interruptor de apagado
    if limits.is_shutdown_active(deps.cfg):
        logger.info("ignorado: interruptor de apagado activo")
        return None

    # 2. Debe empezar por "reto"
    match = _RETO_RE.match(text or "")
    if not match:
        logger.debug("ignorado: mensaje no empieza por 'reto'")
        return None
    remainder = text[match.end():].strip()

    # 3. REGLA PRINCIPAL: sin historia activa, silencio total
    story = blackstorie.read_story(deps.cfg)
    if not story.is_active:
        logger.info("ignorado: sin historia activa")
        return None

    story_hash = story.story_hash
    assert story_hash is not None

    # 4. Deduplicado de message_id (Meta puede reenviar mensajes)
    if db.is_duplicate_message(deps.conn, message_id):
        logger.info("ignorado: message_id duplicado (%s)", message_id)
        return None

    # 5. Limites de ritmo, tope diario y tope de preguntas
    rate_check = limits.check_rate_limit(deps.conn, user_id, deps.cfg)
    if not rate_check.allowed:
        logger.info("ignorado: limite de ritmo superado para %s", user_id)
        db.mark_message_processed(deps.conn, message_id, user_id)
        db.log_interaction(
            deps.conn, user_id=user_id, message_id=message_id, story_hash=story_hash,
            raw_text=text, category="limite_ritmo", response_text=None,
        )
        deps.conn.commit()
        return None

    daily_check = limits.check_daily_global_limit(deps.conn, deps.cfg)
    if not daily_check.allowed:
        logger.info("ignorado: limite diario global superado")
        db.mark_message_processed(deps.conn, message_id, user_id)
        db.log_interaction(
            deps.conn, user_id=user_id, message_id=message_id, story_hash=story_hash,
            raw_text=text, category="limite_diario", response_text=None,
        )
        deps.conn.commit()
        return None

    cap_check = limits.check_question_cap(deps.conn, user_id, story_hash, deps.cfg)
    if not cap_check.allowed:
        response = perso.fixed("tope_preguntas")
        _finish(deps, user_id, message_id, story_hash, text, "tope_preguntas", response)
        return response

    # 6. Interceptores de codigo (sin llamar a la IA)
    normalized_remainder = _normalize_keyword(remainder)

    if normalized_remainder == "":
        response = perso.fixed("bienvenida")
        _finish(deps, user_id, message_id, story_hash, text, "bienvenida", response)
        return response

    if normalized_remainder in _HELP_KEYWORDS:
        response = perso.fixed("ayuda")
        _finish(deps, user_id, message_id, story_hash, text, "ayuda", response)
        return response

    if normalized_remainder in _SOLUTION_KEYWORDS or normalized_remainder.startswith("solucion"):
        response = perso.fixed("me_rindo")
        _finish(deps, user_id, message_id, story_hash, text, "solicitud_solucion", response)
        return response

    if normalized_remainder in _GIVE_UP_KEYWORDS:
        db.set_gave_up(deps.conn, user_id, story_hash)
        response = perso.fixed("me_rindo")
        _finish(deps, user_id, message_id, story_hash, text, "me_rindo", response)
        return response

    # 7. Primera llamada a la IA: arbitro, salida forzada
    try:
        category = deps.model.classify_question(remainder, story.normalized_text)
    except ModelError as exc:
        logger.error("fallo del modelo (arbitro): %s", exc)
        response = perso.fixed("fallo_tecnico")
        _finish(deps, user_id, message_id, story_hash, text, "fallo_tecnico", response, count_question=False)
        return response

    db.increment_questions(deps.conn, user_id, story_hash)

    if category in ("si", "no", "irrelevante", "no_puedo"):
        response = perso.pick(category)
        _finish(deps, user_id, message_id, story_hash, text, category, response, already_counted=True)
        return response

    if category != "intento_solucion":
        # Salvaguarda defensiva: categoria desconocida -> fallo tecnico
        logger.error("categoria desconocida devuelta por el modelo: %r", category)
        response = perso.fixed("fallo_tecnico")
        _finish(deps, user_id, message_id, story_hash, text, "fallo_tecnico", response, already_counted=True)
        return response

    # 8. Segunda llamada: comprobador de intentos de solucion
    try:
        result: GuessCheckResult = deps.model.check_guess(remainder, story.normalized_text)
    except ModelError as exc:
        logger.error("fallo del modelo (comprobador): %s", exc)
        response = perso.fixed("fallo_tecnico")
        _finish(deps, user_id, message_id, story_hash, text, "fallo_tecnico", response, already_counted=True)
        return response

    if result.victoria:
        db.set_won(deps.conn, user_id, story_hash)
        response = perso.fixed("victoria")
        _finish(deps, user_id, message_id, story_hash, text, "intento_solucion_victoria", response, already_counted=True)
        return response

    response = perso.pick("intento_fallido")
    _finish(deps, user_id, message_id, story_hash, text, "intento_solucion_fallido", response, already_counted=True)
    return response


def _finish(
    deps: _Dependencies,
    user_id: str,
    message_id: str | None,
    story_hash: str,
    raw_text: str,
    category: str,
    response_text: str | None,
    *,
    count_question: bool = False,
    already_counted: bool = False,
) -> None:
    if count_question and not already_counted:
        db.increment_questions(deps.conn, user_id, story_hash)
    db.mark_message_processed(deps.conn, message_id, user_id)
    db.log_interaction(
        deps.conn,
        user_id=user_id,
        message_id=message_id,
        story_hash=story_hash,
        raw_text=raw_text,
        category=category,
        response_text=response_text,
    )
    deps.conn.commit()
