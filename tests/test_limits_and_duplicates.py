from __future__ import annotations

import uuid

from core.engine import handle_message
from tests.models_fake import RaisingModel, ScriptedModel


def _mid() -> str:
    return uuid.uuid4().hex


def test_duplicado_de_message_id_se_ignora(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = ScriptedModel(classify_result="si")
    mid = _mid()

    r1 = handle_message("u1", mid, "reto ¿es X?", cfg=cfg, model=model, conn=conn, personality=personality)
    r2 = handle_message("u1", mid, "reto ¿es X?", cfg=cfg, model=model, conn=conn, personality=personality)

    assert r1 is not None
    assert r2 is None
    assert len(model.classify_calls) == 1


def test_tope_de_preguntas_por_historia(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    small_cfg = cfg.__class__(**{**cfg.__dict__, "max_questions_per_story": 2})
    model = ScriptedModel(classify_result="si")

    for _ in range(2):
        r = handle_message(
            "u1", _mid(), "reto ¿es X?", cfg=small_cfg, model=model, conn=conn, personality=personality
        )
        assert r in personality.respuestas["si"]

    r3 = handle_message(
        "u1", _mid(), "reto ¿es X?", cfg=small_cfg, model=model, conn=conn, personality=personality
    )
    assert r3 == personality.fixed("tope_preguntas")
    assert len(model.classify_calls) == 2  # la 3a pregunta no llego a la IA


def test_limite_de_ritmo_por_minuto(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    small_cfg = cfg.__class__(**{**cfg.__dict__, "rate_limit_per_minute": 2})
    model = ScriptedModel(classify_result="si")

    r1 = handle_message("u1", _mid(), "reto ¿a?", cfg=small_cfg, model=model, conn=conn, personality=personality)
    r2 = handle_message("u1", _mid(), "reto ¿b?", cfg=small_cfg, model=model, conn=conn, personality=personality)
    r3 = handle_message("u1", _mid(), "reto ¿c?", cfg=small_cfg, model=model, conn=conn, personality=personality)

    assert r1 is not None
    assert r2 is not None
    assert r3 is None  # tercer mensaje en el mismo minuto: descartado
    assert len(model.classify_calls) == 2


def test_limite_diario_global(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    small_cfg = cfg.__class__(
        **{**cfg.__dict__, "daily_global_limit": 2, "rate_limit_per_minute": 100}
    )
    model = ScriptedModel(classify_result="si")

    handle_message("u1", _mid(), "reto ¿a?", cfg=small_cfg, model=model, conn=conn, personality=personality)
    handle_message("u2", _mid(), "reto ¿b?", cfg=small_cfg, model=model, conn=conn, personality=personality)
    r3 = handle_message("u3", _mid(), "reto ¿c?", cfg=small_cfg, model=model, conn=conn, personality=personality)

    assert r3 is None
    assert len(model.classify_calls) == 2
