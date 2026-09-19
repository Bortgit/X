"""Bateria de pruebas contra el MODELO REAL configurado (MODEL_PROVIDER).

No es parte de la suite de pytest (esa usa siempre modelos simulados). Este
runner llama de verdad al proveedor de IA configurado en .env, con salida
forzada, para medir la calidad de clasificacion sobre una historia y un
lote de casos.

Uso:
    python -m tests.run_battery --story tests/fixtures/story_1.txt --cases tests/fixtures/cases_1.json

Aprobado si: 0 victorias falsas Y al menos 90% de respuestas correctas.
Si no hay modelo configurado (MODEL_PROVIDER=none), o la historia esta
vacia, lo indica claramente y termina sin fallar (exit code 0).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.blackstorie import decode_bytes
from core.config import settings
from core.llm import ModelError, build_model

PASS_MIN_CORRECT_RATIO = 0.90


def load_story_text(path: Path) -> str:
    raw = path.read_bytes()
    text, _ = decode_bytes(raw)
    return text.strip()


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_battery(story_text: str, cases: list[dict], model) -> dict:
    total = len(cases)
    correct = 0
    victorias_falsas = 0
    victorias_negadas = 0
    details = []

    for case in cases:
        text = case["text"]
        expected_category = case["expected_category"]
        try:
            predicted_category = model.classify_question(text, story_text)
        except ModelError as exc:
            details.append({"text": text, "error": str(exc), "correct": False})
            continue

        case_correct = predicted_category == expected_category
        victoria_predicha = None
        victoria_esperada = case.get("expected_victoria")

        if expected_category == "intento_solucion" and predicted_category == "intento_solucion":
            try:
                result = model.check_guess(text, story_text)
                victoria_predicha = result.victoria
            except ModelError as exc:
                details.append({"text": text, "error": str(exc), "correct": False})
                continue
            if victoria_esperada is not None:
                if victoria_predicha != victoria_esperada:
                    case_correct = False
                if victoria_predicha and not victoria_esperada:
                    victorias_falsas += 1
                if (not victoria_predicha) and victoria_esperada:
                    victorias_negadas += 1

        if case_correct:
            correct += 1

        details.append(
            {
                "text": text,
                "expected_category": expected_category,
                "predicted_category": predicted_category,
                "expected_victoria": victoria_esperada,
                "predicted_victoria": victoria_predicha,
                "correct": case_correct,
            }
        )

    ratio = correct / total if total else 0.0
    aprobado = victorias_falsas == 0 and ratio >= PASS_MIN_CORRECT_RATIO

    return {
        "total": total,
        "correct": correct,
        "ratio": ratio,
        "victorias_falsas": victorias_falsas,
        "victorias_negadas": victorias_negadas,
        "aprobado": aprobado,
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bateria de pruebas contra el modelo real")
    parser.add_argument("--story", required=True, help="Ruta al archivo de la historia (texto libre)")
    parser.add_argument("--cases", required=True, help="Ruta al archivo JSON de casos")
    parser.add_argument("--verbose", action="store_true", help="Muestra el detalle de cada caso")
    args = parser.parse_args(argv)

    story_path = Path(args.story)
    cases_path = Path(args.cases)

    story_text = load_story_text(story_path)
    if not story_text:
        print(f"SIN HISTORIA: {story_path} esta vacio (o solo espacios/BOM). No hay nada que evaluar.")
        return 0

    if settings.model_provider == "none":
        print(
            "SIN MODELO CONFIGURADO: MODEL_PROVIDER=none en .env. "
            "Configura 'ollama' o 'claude' para ejecutar la bateria contra un modelo real."
        )
        return 0

    try:
        model = build_model(settings)
    except ModelError as exc:
        print(f"SIN MODELO CONFIGURADO: {exc}")
        return 0

    cases = load_cases(cases_path)
    result = run_battery(story_text, cases, model)

    print(f"Historia: {story_path}")
    print(f"Casos evaluados: {result['total']}")
    print(f"Respuestas correctas: {result['correct']} ({result['ratio'] * 100:.1f}%)")
    print(f"Victorias falsas (victoria concedida sin merecerlo): {result['victorias_falsas']}")
    print(f"Victorias negadas (solucion correcta no reconocida): {result['victorias_negadas']}")
    print(f"Resultado: {'APROBADO' if result['aprobado'] else 'NO APROBADO'}")

    if args.verbose:
        for detail in result["details"]:
            print(detail)

    return 0 if result["aprobado"] else 1


if __name__ == "__main__":
    sys.exit(main())
