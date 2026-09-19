"""Configuracion central del bot, leida desde variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv es una dependencia declarada
    load_dotenv = None

# Raiz del proyecto = carpeta que contiene esta carpeta "core"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(root: Path) -> None:
    env_path = root / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


_load_env_file(PROJECT_ROOT)


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT

    # Regla principal: carpeta y archivo de la historia activa
    blackstorie_dir_name: str = os.getenv("BLACKSTORIE_DIR", "blackstorie")
    blackstorie_file_name: str = os.getenv("BLACKSTORIE_FILE", "blackstorie.txt")
    blackstorie_readme_name: str = os.getenv("BLACKSTORIE_README", "LEEME.txt")
    max_story_chars: int = _env_int("MAX_STORY_CHARS", 20000)

    # Base de datos
    db_path: str = os.getenv("DB_PATH", "blackstories.db")

    # Modelo / proveedor de IA
    model_provider: str = os.getenv("MODEL_PROVIDER", "none").strip().lower()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    model_timeout_seconds: float = float(os.getenv("MODEL_TIMEOUT_SECONDS", "20"))

    # Proteccciones / limites
    max_questions_per_story: int = _env_int("MAX_QUESTIONS_PER_STORY", 40)
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 6)
    daily_global_limit: int = _env_int("DAILY_GLOBAL_LIMIT", 500)

    # Interruptor de apagado
    shutdown_env_var: str = "BOT_SHUTDOWN"
    shutdown_file_name: str = os.getenv("SHUTDOWN_FILE", "SHUTDOWN")

    # Instagram / Meta
    ig_verify_token: str = os.getenv("IG_VERIFY_TOKEN", "")
    ig_app_secret: str = os.getenv("IG_APP_SECRET", "")
    ig_page_access_token: str = os.getenv("IG_PAGE_ACCESS_TOKEN", "")
    ig_graph_api_version: str = os.getenv("IG_GRAPH_API_VERSION", "v21.0")

    personality_path: str = os.getenv("PERSONALITY_FILE", "personality.yaml")
    arbiter_prompt_path: str = os.getenv("ARBITER_PROMPT_FILE", "prompts/arbiter.md")
    guess_checker_prompt_path: str = os.getenv(
        "GUESS_CHECKER_PROMPT_FILE", "prompts/guess_checker.md"
    )

    def resolve(self, relative: str) -> Path:
        return self.project_root / relative

    @property
    def blackstorie_dir(self) -> Path:
        return self.project_root / self.blackstorie_dir_name

    @property
    def blackstorie_file(self) -> Path:
        return self.blackstorie_dir / self.blackstorie_file_name

    @property
    def blackstorie_readme(self) -> Path:
        return self.blackstorie_dir / self.blackstorie_readme_name

    @property
    def shutdown_file(self) -> Path:
        return self.project_root / self.shutdown_file_name


def get_settings() -> Settings:
    """Devuelve una configuracion nueva leyendo el entorno actual (util en tests)."""
    return Settings()


settings = get_settings()
