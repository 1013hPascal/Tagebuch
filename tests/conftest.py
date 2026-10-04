"""Gemeinsame Fixtures für die Tests."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from kern.config import Config
from kern.speicher import Speicher
from ui.announcer import announcer


@pytest.fixture(autouse=True)
def _announcer_zuruecksetzen():
    """`announcer` ist ein Modul-Singleton (Abschnitt 11): `target` zeigt meist auf ein
    HauptFenster, das am Testende von Qt zerstört wird. Ohne Reset zeigt `target` danach auf
    ein bereits gelöschtes C++-Objekt, und der nächste Test, der `announce()` aufruft, stürzt ab."""
    yield
    announcer.target = None


@pytest.fixture
def speicher(tmp_path):
    s = Speicher(tmp_path / "tagebuch.db")
    yield s
    try:
        s.close()
    except Exception:
        pass


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("TAGEBUCH_HOME", str(tmp_path))
    return Config.load(pfad=tmp_path / "config.toml")
