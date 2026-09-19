from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.config import Settings
from core import db as db_mod
from core.personality import load_personality


@pytest.fixture
def cfg(tmp_path):
    """Configuracion aislada en una ruta temporal (nunca toca el proyecto real)."""
    return Settings(
        project_root=tmp_path,
        blackstorie_dir_name="blackstorie",
        blackstorie_file_name="blackstorie.txt",
        blackstorie_readme_name="LEEME.txt",
        max_story_chars=20000,
        db_path=":memory:",
        model_provider="none",
        max_questions_per_story=5,
        rate_limit_per_minute=3,
        daily_global_limit=1000,
        shutdown_file_name="SHUTDOWN",
    )


@pytest.fixture
def conn(cfg):
    connection = db_mod.get_connection(cfg)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def personality():
    """Carga el personality.yaml REAL del proyecto (valida que sea correcto)."""
    real_cfg = Settings(project_root=REPO_ROOT)
    return load_personality(real_cfg)


def write_story(cfg: Settings, content: str, encoding: str = "utf-8") -> None:
    cfg.blackstorie_dir.mkdir(parents=True, exist_ok=True)
    if encoding == "utf-8":
        cfg.blackstorie_file.write_text(content, encoding="utf-8")
    else:
        cfg.blackstorie_file.write_bytes(content.encode(encoding))
