"""Tests für ki/warteschlange.py."""
from __future__ import annotations

from kern.modelle import EintragTyp
from ki.warteschlange import Auftrag, Warteschlange


def _auftrag(zeitraum: str) -> Auftrag:
    return Auftrag(EintragTyp.TAG, zeitraum, f"Beschreibung {zeitraum}", lambda: None)


def test_neue_warteschlange_ist_leer():
    warteschlange = Warteschlange()
    assert warteschlange.ist_leer() is True
    assert len(warteschlange) == 0


def test_fifo_reihenfolge():
    warteschlange = Warteschlange()
    warteschlange.hinzufuegen(_auftrag("2026-09-20"))
    warteschlange.hinzufuegen(_auftrag("2026-09-21"))
    assert len(warteschlange) == 2
    assert warteschlange.naechster().zeitraum == "2026-09-20"
    assert warteschlange.naechster().zeitraum == "2026-09-21"
    assert warteschlange.ist_leer() is True
