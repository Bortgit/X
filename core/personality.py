"""Carga personality.yaml y elige variantes de respuesta al azar.

La IA nunca escribe texto libre al jugador: todo lo que ve sale de aqui.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from core.config import Settings, settings as default_settings

# Categorias de respuesta de juego (variantes, elegidas al azar)
GAME_CATEGORIES = ("si", "no", "irrelevante", "no_puedo", "intento_fallido")

# Mensajes fijos de sistema (uno solo cada uno, sin variantes)
FIXED_MESSAGES = (
    "bienvenida",
    "ayuda",
    "victoria",
    "tope_preguntas",
    "me_rindo",
    "fallo_tecnico",
)


@dataclass
class Personality:
    respuestas: dict[str, list[str]]
    mensajes_fijos: dict[str, str]

    def pick(self, category: str) -> str:
        variants = self.respuestas.get(category)
        if not variants:
            raise KeyError(f"Sin variantes de personalidad para la categoria '{category}'")
        return random.choice(variants)

    def fixed(self, name: str) -> str:
        try:
            return self.mensajes_fijos[name]
        except KeyError as exc:
            raise KeyError(f"Sin mensaje fijo de personalidad llamado '{name}'") from exc


def load_personality(cfg: Settings | None = None) -> Personality:
    cfg = cfg or default_settings
    path = cfg.resolve(cfg.personality_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    respuestas = data.get("respuestas", {})
    mensajes_fijos = data.get("mensajes_fijos", {})

    missing_categories = [c for c in GAME_CATEGORIES if not respuestas.get(c)]
    if missing_categories:
        raise ValueError(
            f"personality.yaml no tiene variantes para: {missing_categories}"
        )
    missing_fixed = [m for m in FIXED_MESSAGES if not mensajes_fijos.get(m)]
    if missing_fixed:
        raise ValueError(
            f"personality.yaml no tiene mensajes fijos para: {missing_fixed}"
        )

    return Personality(respuestas=respuestas, mensajes_fijos=mensajes_fijos)
