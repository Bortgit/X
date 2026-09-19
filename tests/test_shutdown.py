from __future__ import annotations

import uuid

from core.engine import handle_message
from tests.models_fake import RaisingModel


def _mid() -> str:
    return uuid.uuid4().hex


def test_interruptor_por_variable_de_entorno(cfg, conn, personality, monkeypatch):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    monkeypatch.setenv(cfg.shutdown_env_var, "1")

    response = handle_message(
        "u1", _mid(), "reto ¿es X?", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert response is None


def test_interruptor_por_archivo(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    cfg.shutdown_file.write_text("apagado", encoding="utf-8")

    response = handle_message(
        "u1", _mid(), "reto ¿es X?", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert response is None


def test_sin_interruptor_responde_normalmente(cfg, conn, personality, monkeypatch):
    monkeypatch.delenv(cfg.shutdown_env_var, raising=False)
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    from tests.models_fake import ScriptedModel

    response = handle_message(
        "u1", _mid(), "reto ¿es X?", cfg=cfg, model=ScriptedModel(classify_result="si"),
        conn=conn, personality=personality,
    )
    assert response is not None
