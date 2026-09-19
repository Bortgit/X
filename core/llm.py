"""Abstraccion del modelo de IA (arbitro + comprobador de solucion).

Dos backends intercambiables por configuracion (MODEL_PROVIDER en .env):
  - "ollama": local, usa el parametro `format` con un esquema JSON (salida
    forzada por enum).
  - "claude": API de Anthropic, usa tool use obligatorio (tool_choice) con
    un esquema de entrada que restringe la categoria a un enum.

La IA NUNCA genera el texto que ve el jugador: solo devuelve una categoria
(o un veredicto estructurado interno para el comprobador de soluciones).
Las plantillas de texto viven en personality.yaml.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from core.config import Settings, settings as default_settings

CATEGORIES = ("si", "no", "irrelevante", "no_puedo", "intento_solucion")

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "categoria": {"type": "string", "enum": list(CATEGORIES)},
    },
    "required": ["categoria"],
    "additionalProperties": False,
}

GUESS_SCHEMA = {
    "type": "object",
    "properties": {
        "hechos_clave": {"type": "array", "items": {"type": "string"}},
        "hechos_cubiertos": {"type": "array", "items": {"type": "string"}},
        "victoria": {"type": "boolean"},
    },
    "required": ["hechos_clave", "hechos_cubiertos", "victoria"],
    "additionalProperties": False,
}


class ModelError(Exception):
    """Fallo del modelo (timeout, respuesta invalida, sin conexion, etc.)."""


@dataclass(frozen=True)
class GuessCheckResult:
    hechos_clave: list[str] = field(default_factory=list)
    hechos_cubiertos: list[str] = field(default_factory=list)
    victoria: bool = False


class BaseModel(ABC):
    """Interfaz que deben implementar todos los backends de IA."""

    @abstractmethod
    def classify_question(self, question: str, story_text: str) -> str:
        """Devuelve una de CATEGORIES."""

    @abstractmethod
    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        """Comprueba un intento de solucion contra la historia."""


def _load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_prompt(template: str, story_text: str) -> str:
    return template.replace("{HISTORIA}", story_text)


class NoProviderModel(BaseModel):
    """Se usa cuando MODEL_PROVIDER no esta configurado. Falla explicitamente."""

    def classify_question(self, question: str, story_text: str) -> str:
        raise ModelError(
            "No hay ningun proveedor de IA configurado (MODEL_PROVIDER en .env)."
        )

    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        raise ModelError(
            "No hay ningun proveedor de IA configurado (MODEL_PROVIDER en .env)."
        )


class OllamaModel(BaseModel):
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.arbiter_template = _load_prompt_template(cfg.resolve(cfg.arbiter_prompt_path))
        self.guess_template = _load_prompt_template(
            cfg.resolve(cfg.guess_checker_prompt_path)
        )

    def _chat(self, system_prompt: str, user_message: str, schema: dict) -> dict:
        import httpx

        payload = {
            "model": self.cfg.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "format": schema,
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{self.cfg.ollama_host}/api/chat",
                json=payload,
                timeout=self.cfg.model_timeout_seconds,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - requiere Ollama real
            raise ModelError(f"Error llamando a Ollama: {exc}") from exc

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ModelError(f"Respuesta de Ollama no es JSON valido: {content!r}") from exc

    def classify_question(self, question: str, story_text: str) -> str:
        system_prompt = _render_prompt(self.arbiter_template, story_text)
        result = self._chat(system_prompt, question, CLASSIFY_SCHEMA)
        categoria = result.get("categoria")
        if categoria not in CATEGORIES:
            raise ModelError(f"Categoria invalida devuelta por Ollama: {categoria!r}")
        return categoria

    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        system_prompt = _render_prompt(self.guess_template, story_text)
        result = self._chat(system_prompt, guess_text, GUESS_SCHEMA)
        return GuessCheckResult(
            hechos_clave=list(result.get("hechos_clave", [])),
            hechos_cubiertos=list(result.get("hechos_cubiertos", [])),
            victoria=bool(result.get("victoria", False)),
        )


class ClaudeModel(BaseModel):
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.arbiter_template = _load_prompt_template(cfg.resolve(cfg.arbiter_prompt_path))
        self.guess_template = _load_prompt_template(
            cfg.resolve(cfg.guess_checker_prompt_path)
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover
                raise ModelError(
                    "El paquete 'anthropic' no esta instalado (pip install anthropic)."
                ) from exc
            if not self.cfg.anthropic_api_key:
                raise ModelError("Falta ANTHROPIC_API_KEY en .env")
            self._client = anthropic.Anthropic(api_key=self.cfg.anthropic_api_key)
        return self._client

    def _tool_call(
        self, system_prompt: str, user_message: str, tool_name: str, schema: dict
    ) -> dict:
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self.cfg.anthropic_model,
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[
                    {
                        "name": tool_name,
                        "description": "Devuelve el veredicto estructurado.",
                        "input_schema": schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
                timeout=self.cfg.model_timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - requiere API real
            raise ModelError(f"Error llamando a la API de Claude: {exc}") from exc

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return block.input
        raise ModelError("Claude no devolvio un tool_use con el nombre esperado.")

    def classify_question(self, question: str, story_text: str) -> str:
        system_prompt = _render_prompt(self.arbiter_template, story_text)
        result = self._tool_call(system_prompt, question, "clasificar_pregunta", CLASSIFY_SCHEMA)
        categoria = result.get("categoria")
        if categoria not in CATEGORIES:
            raise ModelError(f"Categoria invalida devuelta por Claude: {categoria!r}")
        return categoria

    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        system_prompt = _render_prompt(self.guess_template, story_text)
        result = self._tool_call(
            system_prompt, guess_text, "comprobar_solucion", GUESS_SCHEMA
        )
        return GuessCheckResult(
            hechos_clave=list(result.get("hechos_clave", [])),
            hechos_cubiertos=list(result.get("hechos_cubiertos", [])),
            victoria=bool(result.get("victoria", False)),
        )


def build_model(cfg: Settings | None = None) -> BaseModel:
    cfg = cfg or default_settings
    provider = cfg.model_provider
    if provider == "ollama":
        return OllamaModel(cfg)
    if provider == "claude":
        return ClaudeModel(cfg)
    return NoProviderModel()
