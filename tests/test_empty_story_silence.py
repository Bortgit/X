"""Con blackstorie.txt vacio (sin juego), el bot debe callar SIEMPRE:
sin llamar a la IA, sin crear sesion, sin contar en limites."""
from __future__ import annotations

import pytest

from core import blackstorie, db
from core.engine import handle_message
from tests.models_fake import RaisingModel


@pytest.mark.parametrize(
    "text",
    [
        "reto ¿es un asesinato?",
        "RETO",
        "reto ayuda",
        "reto me rindo",
        "reto solución",
        "reto solucion",
        "Reto: ¿estaba solo?",
        "RETO, ¿fue un accidente?",
    ],
)
def test_sin_historia_activa_no_responde_nada(cfg, conn, personality, text):
    blackstorie.ensure_blackstorie_files(cfg)  # archivo vacio
    model = RaisingModel()  # si se llama, el test falla

    response = handle_message(
        "user-1", "msg-1", text, cfg=cfg, model=model, conn=conn, personality=personality
    )

    assert response is None
    # No debe haberse creado sesion de jugador ni registro alguno
    assert conn.execute("SELECT COUNT(*) c FROM player_progress").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM interaction_log").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM processed_messages").fetchone()["c"] == 0


@pytest.mark.parametrize("whitespace", ["", "   ", "\n\n\t", "﻿", "﻿   \n"])
def test_archivo_solo_espacios_o_bom_no_responde(cfg, conn, personality, whitespace):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_bytes(whitespace.encode("utf-8"))
    model = RaisingModel()

    response = handle_message(
        "user-1", "msg-1", "reto ¿es un asesinato?", cfg=cfg, model=model, conn=conn, personality=personality
    )
    assert response is None


def test_mensajes_sin_reto_no_responden_ni_con_historia_activa(cfg, conn, personality):
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    model = RaisingModel()

    for text in [
        "hola, cuanto cuesta el adiestramiento?",
        "necesito ayuda con mi perro",
        "retorno del enigma",  # no debe confundirse con "reto"
        "",
    ]:
        response = handle_message(
            "user-1", "msg-x", text, cfg=cfg, model=model, conn=conn, personality=personality
        )
        assert response is None
