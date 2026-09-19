"""REGLA PRINCIPAL: creacion automatica, no sobrescritura y lectura tolerante
del archivo blackstorie.txt."""
from __future__ import annotations

from core import blackstorie


def test_crea_carpeta_y_archivo_vacio(cfg):
    assert not cfg.blackstorie_dir.exists()
    blackstorie.ensure_blackstorie_files(cfg)
    assert cfg.blackstorie_dir.is_dir()
    assert cfg.blackstorie_file.exists()
    assert cfg.blackstorie_file.stat().st_size == 0
    assert cfg.blackstorie_readme.exists()
    assert cfg.blackstorie_readme.stat().st_size > 0


def test_no_sobrescribe_archivo_existente(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_text("ENIGMA: algo\nSOLUCION: algo mas", encoding="utf-8")
    blackstorie.ensure_blackstorie_files(cfg)
    assert cfg.blackstorie_file.read_text(encoding="utf-8") == "ENIGMA: algo\nSOLUCION: algo mas"


def test_no_sobrescribe_leeme_existente(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_readme.write_text("mis notas personales", encoding="utf-8")
    blackstorie.ensure_blackstorie_files(cfg)
    assert cfg.blackstorie_readme.read_text(encoding="utf-8") == "mis notas personales"


def test_llamadas_repetidas_son_idempotentes(cfg):
    blackstorie.ensure_blackstorie_files(cfg)
    blackstorie.ensure_blackstorie_files(cfg)
    blackstorie.ensure_blackstorie_files(cfg)
    assert cfg.blackstorie_file.stat().st_size == 0


def test_archivo_vacio_es_inactivo(cfg):
    blackstorie.ensure_blackstorie_files(cfg)
    state = blackstorie.read_story(cfg)
    assert state.is_active is False
    assert state.story_hash is None


def test_archivo_solo_espacios_es_inactivo(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_text("   \n\t  \n   ", encoding="utf-8")
    state = blackstorie.read_story(cfg)
    assert state.is_active is False


def test_archivo_solo_bom_es_inactivo(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_bytes(b"\xef\xbb\xbf")
    state = blackstorie.read_story(cfg)
    assert state.is_active is False


def test_archivo_con_contenido_es_activo(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    state = blackstorie.read_story(cfg)
    assert state.is_active is True
    assert state.char_count > 0
    assert state.story_hash is not None


def test_lectura_utf8_con_bom(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    content = "ENIGMA: la niña\nSOLUCION: fue un sueño"
    cfg.blackstorie_file.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    state = blackstorie.read_story(cfg)
    assert state.is_active is True
    assert "niña" in state.normalized_text
    assert state.encoding_used == "utf-8"


def test_lectura_cp1252(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    content = "ENIGMA: la señora tomó café\nSOLUCION: murió de risa"
    cfg.blackstorie_file.write_bytes(content.encode("cp1252"))
    state = blackstorie.read_story(cfg)
    assert state.is_active is True
    assert "señora" in state.normalized_text
    assert "café" in state.normalized_text
    assert state.encoding_used == "cp1252"


def test_hash_ignora_espacios_alrededor(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_text("  ENIGMA: X\nSOLUCION: Y  \n\n", encoding="utf-8")
    state1 = blackstorie.read_story(cfg)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    state2 = blackstorie.read_story(cfg)
    assert state1.story_hash == state2.story_hash


def test_hash_cambia_con_contenido_distinto(cfg):
    cfg.blackstorie_dir.mkdir(parents=True)
    cfg.blackstorie_file.write_text("ENIGMA: X\nSOLUCION: Y", encoding="utf-8")
    state1 = blackstorie.read_story(cfg)
    cfg.blackstorie_file.write_text("ENIGMA: Z\nSOLUCION: W", encoding="utf-8")
    state2 = blackstorie.read_story(cfg)
    assert state1.story_hash != state2.story_hash


def test_aviso_si_supera_max_chars(cfg, caplog):
    cfg.blackstorie_dir.mkdir(parents=True)
    long_text = "ENIGMA: " + ("x" * 25)
    small_cfg = cfg.__class__(**{**cfg.__dict__, "max_story_chars": 10})
    cfg.blackstorie_file.write_text(long_text, encoding="utf-8")
    with caplog.at_level("WARNING"):
        state = blackstorie.read_story(small_cfg)
    assert state.is_active is True
    assert any("supera" in rec.message for rec in caplog.records)
