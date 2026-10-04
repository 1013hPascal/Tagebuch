"""Tests für ui/ki_worker.py (Abschnitt 9 des Konzepts)."""
from __future__ import annotations

from kern.modelle import EintragTyp
from ki.ollama_client import OllamaFehler
from ki.warteschlange import Auftrag
from ui.ki_worker import KiWarteschlangenVerarbeiter


def _auftrag(zeitraum: str, ausfuehren) -> Auftrag:
    return Auftrag(EintragTyp.TAG, zeitraum, f"Erstelle Stichpunkte für {zeitraum} …", ausfuehren)


def _bis_ruhig(verarbeiter: KiWarteschlangenVerarbeiter, qtbot, timeout: int = 2000) -> None:
    """Wartet, bis kein Hintergrund-Task mehr läuft. Ein QThread darf beim Testende nicht
    noch aktiv sein - sonst kann der Prozess beim Aufräumen abstürzen."""
    qtbot.waitUntil(lambda: verarbeiter._task is None, timeout=timeout)


def test_einzelner_auftrag_wird_erledigt(qtbot):
    verarbeiter = KiWarteschlangenVerarbeiter()
    erledigt = []

    verarbeiter.auftrag_fertig.connect(lambda typ, zeitraum: erledigt.append((typ, zeitraum)))
    verarbeiter.hinzufuegen(_auftrag("2026-09-20", lambda: None))

    qtbot.waitUntil(lambda: erledigt == [(EintragTyp.TAG, "2026-09-20")], timeout=2000)
    _bis_ruhig(verarbeiter, qtbot)


def test_mehrere_auftraege_laufen_nacheinander(qtbot):
    verarbeiter = KiWarteschlangenVerarbeiter()
    reihenfolge = []

    verarbeiter.hinzufuegen(_auftrag("2026-09-20", lambda: reihenfolge.append("1")))
    verarbeiter.hinzufuegen(_auftrag("2026-09-21", lambda: reihenfolge.append("2")))

    qtbot.waitUntil(lambda: reihenfolge == ["1", "2"], timeout=2000)
    _bis_ruhig(verarbeiter, qtbot)


def test_nicht_erreichbar_wird_einmalig_gemeldet_und_haelt_an(qtbot):
    verarbeiter = KiWarteschlangenVerarbeiter()
    meldungen = []
    erledigt = []

    def schlaegt_fehl():
        raise OllamaFehler("nicht erreichbar")

    verarbeiter.nicht_erreichbar.connect(lambda: meldungen.append(True))
    verarbeiter.auftrag_fertig.connect(lambda typ, zeitraum: erledigt.append(zeitraum))

    verarbeiter.hinzufuegen(_auftrag("2026-09-20", schlaegt_fehl))
    qtbot.waitUntil(lambda: len(meldungen) == 1, timeout=2000)
    _bis_ruhig(verarbeiter, qtbot)

    # Zweiter, gleichzeitig eingereihter Auftrag wird fuer diese Sitzung nicht mehr automatisch versucht.
    verarbeiter._warteschlange.hinzufuegen(_auftrag("2026-09-21", lambda: erledigt.append("2026-09-21")))
    qtbot.wait(300)
    assert erledigt == []
    assert meldungen == [True]


def test_status_wird_vor_der_ausfuehrung_gemeldet(qtbot):
    verarbeiter = KiWarteschlangenVerarbeiter()
    status = []
    fertig = []
    verarbeiter.status_geaendert.connect(status.append)
    verarbeiter.auftrag_fertig.connect(lambda typ, zeitraum: fertig.append(zeitraum))

    verarbeiter.hinzufuegen(_auftrag("2026-09-20", lambda: None))
    qtbot.waitUntil(lambda: status == ["Erstelle Stichpunkte für 2026-09-20 …"], timeout=2000)
    qtbot.waitUntil(lambda: fertig == ["2026-09-20"], timeout=2000)
    _bis_ruhig(verarbeiter, qtbot)


def test_unerwarteter_fehler_haelt_warteschlange_nicht_dauerhaft_an(qtbot):
    verarbeiter = KiWarteschlangenVerarbeiter()
    erledigt = []

    def wirft_unerwarteten_fehler():
        raise RuntimeError("Bug")

    verarbeiter.hinzufuegen(_auftrag("2026-09-20", wirft_unerwarteten_fehler))
    verarbeiter.hinzufuegen(_auftrag("2026-09-21", lambda: erledigt.append("2026-09-21")))

    qtbot.waitUntil(lambda: erledigt == ["2026-09-21"], timeout=2000)
    _bis_ruhig(verarbeiter, qtbot)
