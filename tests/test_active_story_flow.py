"""Con historia activa, el bot responde segun las reglas del pipeline."""
from __future__ import annotations

import uuid

from core import db
from core.engine import handle_message
from core.llm import GuessCheckResult
from tests.models_fake import RaisingModel, ScriptedModel


def _mid() -> str:
    return uuid.uuid4().hex


def test_reto_solo_da_bienvenida_sin_llamar_ia(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    response = handle_message(
        "u1", _mid(), "reto", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert response == personality.fixed("bienvenida")


def test_reto_ayuda_sin_llamar_ia(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    response = handle_message(
        "u1", _mid(), "reto ayuda", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert response == personality.fixed("ayuda")


def test_reto_solucion_no_revela_nada_sin_llamar_ia(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y secreta", encoding="utf-8")
    for text in ["reto solución", "reto solucion", "reto SOLUCIÓN"]:
        response = handle_message(
            "u1", _mid(), text, cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
        )
        assert response == personality.fixed("me_rindo")
        assert "secreta" not in response


def test_reto_me_rindo_sin_llamar_ia_y_marca_gave_up(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    response = handle_message(
        "u1", _mid(), "reto me rindo", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert response == personality.fixed("me_rindo")
    row = conn.execute("SELECT gave_up FROM player_progress WHERE user_id='u1'").fetchone()
    assert row["gave_up"] == 1


def test_pregunta_normal_usa_arbitro_y_responde_categoria(cfg, conn, personality):
    cfg = cfg.__class__(**{**cfg.__dict__, "rate_limit_per_minute": 1000})
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    for categoria in ("si", "no", "irrelevante", "no_puedo"):
        model = ScriptedModel(classify_result=categoria)
        response = handle_message(
            "u1", _mid(), "reto ¿fue un asesinato?", cfg=cfg, model=model, conn=conn, personality=personality
        )
        assert response in personality.respuestas[categoria]
        assert model.classify_calls == ["¿fue un asesinato?"]


def test_intento_solucion_victoria(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = ScriptedModel(
        classify_result="intento_solucion",
        guess_result=GuessCheckResult(hechos_clave=["a"], hechos_cubiertos=["a"], victoria=True),
    )
    response = handle_message(
        "u1", _mid(), "reto creo que fue el mayordomo con el cuchillo",
        cfg=cfg, model=model, conn=conn, personality=personality,
    )
    assert response == personality.fixed("victoria")
    row = conn.execute("SELECT won FROM player_progress WHERE user_id='u1'").fetchone()
    assert row["won"] == 1


def test_intento_solucion_fallido_no_da_victoria(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = ScriptedModel(
        classify_result="intento_solucion",
        guess_result=GuessCheckResult(hechos_clave=["a", "b"], hechos_cubiertos=["a"], victoria=False),
    )
    response = handle_message(
        "u1", _mid(), "reto fue un accidente sin mas",
        cfg=cfg, model=model, conn=conn, personality=personality,
    )
    assert response in personality.respuestas["intento_fallido"]
    row = conn.execute("SELECT won FROM player_progress WHERE user_id='u1'").fetchone()
    assert row["won"] == 0


def test_fallo_tecnico_si_el_arbitro_lanza_error(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = ScriptedModel(raise_on_classify=True)
    response = handle_message(
        "u1", _mid(), "reto ¿fue un asesinato?", cfg=cfg, model=model, conn=conn, personality=personality
    )
    assert response == personality.fixed("fallo_tecnico")


def test_vaciar_y_rellenar_sin_reiniciar_nada(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")

    model = ScriptedModel(classify_result="si")
    r1 = handle_message("u1", _mid(), "reto ¿es X?", cfg=cfg, model=model, conn=conn, personality=personality)
    assert r1 is not None

    # Vaciar el archivo: debe volver a callar de inmediato
    cfg.blackstorie_file.write_text("", encoding="utf-8")
    r2 = handle_message(
        "u1", _mid(), "reto ¿es X?", cfg=cfg, model=RaisingModel(), conn=conn, personality=personality
    )
    assert r2 is None

    # Rellenar de nuevo: debe responder otra vez, sin reiniciar el proceso
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    r3 = handle_message("u1", _mid(), "reto ¿es X?", cfg=cfg, model=model, conn=conn, personality=personality)
    assert r3 is not None


def test_cambiar_historia_reinicia_contadores(cfg, conn, personality):
    cfg = cfg.__class__(**{**cfg.__dict__, "rate_limit_per_minute": 1000})
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = ScriptedModel(classify_result="si")

    for _ in range(3):
        handle_message("u1", _mid(), "reto ¿es X?", cfg=cfg, model=model, conn=conn, personality=personality)

    row = conn.execute(
        "SELECT questions_asked FROM player_progress WHERE user_id='u1'"
    ).fetchone()
    assert row["questions_asked"] == 3

    # Cambiar el contenido: es una historia nueva, el contador para esa
    # historia debe partir de cero (aunque el historial anterior se conserve)
    cfg.blackstorie_file.write_text("ENIGMA: Z\nSOLUCION: W", encoding="utf-8")
    handle_message("u1", _mid(), "reto ¿es Z?", cfg=cfg, model=model, conn=conn, personality=personality)

    rows = conn.execute(
        "SELECT story_hash, questions_asked FROM player_progress WHERE user_id='u1' ORDER BY first_seen"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["questions_asked"] == 3
    assert rows[1]["questions_asked"] == 1
