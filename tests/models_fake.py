"""Modelos de IA simulados para tests: no llaman a ningun servicio real."""
from __future__ import annotations

from core.llm import BaseModel, GuessCheckResult, ModelError


class RaisingModel(BaseModel):
    """Lanza una excepcion si se le llama: demuestra que el motor NO llamo a la IA."""

    def classify_question(self, question: str, story_text: str) -> str:
        raise AssertionError(
            "El modelo NO deberia haber sido llamado (classify_question) para: "
            f"{question!r}"
        )

    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        raise AssertionError(
            "El modelo NO deberia haber sido llamado (check_guess) para: "
            f"{guess_text!r}"
        )


class ScriptedModel(BaseModel):
    """Devuelve resultados prefijados y registra cuantas veces se le llamo."""

    def __init__(
        self,
        classify_result: str = "si",
        guess_result: GuessCheckResult | None = None,
        raise_on_classify: bool = False,
        raise_on_guess: bool = False,
    ):
        self.classify_result = classify_result
        self.guess_result = guess_result or GuessCheckResult(victoria=False)
        self.raise_on_classify = raise_on_classify
        self.raise_on_guess = raise_on_guess
        self.classify_calls: list[str] = []
        self.guess_calls: list[str] = []

    def classify_question(self, question: str, story_text: str) -> str:
        self.classify_calls.append(question)
        if self.raise_on_classify:
            raise ModelError("fallo simulado de arbitro")
        return self.classify_result

    def check_guess(self, guess_text: str, story_text: str) -> GuessCheckResult:
        self.guess_calls.append(guess_text)
        if self.raise_on_guess:
            raise ModelError("fallo simulado de comprobador")
        return self.guess_result
