"""Tests für kern/config.py."""
from __future__ import annotations

from pathlib import Path

from kern.config import Config, app_dir


def test_load_ohne_datei_liefert_standardwerte(tmp_path):
    cfg = Config.load(tmp_path / "gibt_es_nicht.toml")
    assert cfg.ollama_modell == "gemma4:12b"
    assert cfg.whisper_modell == "small"
    assert cfg.max_aufnahme_sekunden == 600


def test_load_mit_kaputter_datei_liefert_standardwerte(tmp_path):
    pfad = tmp_path / "config.toml"
    pfad.write_text("das ist kein gueltiges toml [[[", encoding="utf-8")
    cfg = Config.load(pfad)
    assert cfg.ollama_modell == "gemma4:12b"


def test_save_und_load_roundtrip(tmp_path):
    pfad = tmp_path / "config.toml"
    cfg = Config()
    cfg.ollama_modell = "anderes-modell"
    cfg.max_aufnahme_sekunden = 120
    cfg.save(pfad)

    geladen = Config.load(pfad)
    assert geladen.ollama_modell == "anderes-modell"
    assert geladen.max_aufnahme_sekunden == 120


def test_unbekannte_felder_werden_ignoriert(tmp_path):
    pfad = tmp_path / "config.toml"
    pfad.write_text('unbekanntes_feld = "x"\nollama_modell = "test-modell"\n', encoding="utf-8")
    cfg = Config.load(pfad)
    assert cfg.ollama_modell == "test-modell"
    assert not hasattr(cfg, "unbekanntes_feld")


def test_feld_mit_falschem_typ_wird_ignoriert(tmp_path):
    pfad = tmp_path / "config.toml"
    pfad.write_text('max_aufnahme_sekunden = "keine_zahl"\n', encoding="utf-8")
    cfg = Config.load(pfad)
    assert cfg.max_aufnahme_sekunden == 600


def test_datenbank_pfad_standard(monkeypatch, tmp_path):
    monkeypatch.setenv("TAGEBUCH_HOME", str(tmp_path))
    cfg = Config()
    assert cfg.datenbank_pfad() == tmp_path / "tagebuch.db"


def test_datenbank_pfad_ueberschrieben():
    cfg = Config(db_pfad="C:/irgendwo/meine.db")
    assert cfg.datenbank_pfad() == Path("C:/irgendwo/meine.db")


def test_app_dir_erstellt_verzeichnis(monkeypatch, tmp_path):
    ziel = tmp_path / "unterordner"
    monkeypatch.setenv("TAGEBUCH_HOME", str(ziel))
    ergebnis = app_dir()
    assert ergebnis == ziel
    assert ziel.exists()
