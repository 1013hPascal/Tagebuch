"""Tests für ui/lese_ansicht.py (Abschnitt 7.4 des Konzepts)."""
from __future__ import annotations

from PySide6.QtCore import Qt

from kern.modelle import EintragTyp
from ui.lese_ansicht import LeseAnsicht


def test_anzeigen_setzt_text_namen_und_cursor(qtbot):
    ansicht = LeseAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG, "2026-09-21", "Gestern war ruhig.")
    assert ansicht.text_anzeige.toPlainText() == "Gestern war ruhig."
    assert ansicht.text_anzeige.accessibleName() == "Eintrag vom 21.09.2026"
    assert ansicht.text_anzeige.textCursor().position() == 0
    assert ansicht.text_anzeige.isReadOnly() is True


def test_anzeigen_monat_und_jahr_namen(qtbot):
    ansicht = LeseAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.MONAT, "2026-09", "Text")
    assert ansicht.text_anzeige.accessibleName() == "September 2026"
    ansicht.anzeigen(EintragTyp.JAHR, "2025", "Text")
    assert ansicht.text_anzeige.accessibleName() == "2025"


def test_bearbeiten_knopf_sendet_signal(qtbot):
    ansicht = LeseAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG, "2026-09-21", "Text")

    empfangen = []
    ansicht.bearbeiten_angefordert.connect(lambda typ, zeitraum: empfangen.append((typ, zeitraum)))
    qtbot.mouseClick(ansicht.bearbeiten_knopf, Qt.MouseButton.LeftButton)
    assert empfangen == [(EintragTyp.TAG, "2026-09-21")]


def test_enter_auf_fokussiertem_bearbeiten_knopf_sendet_signal(qtbot):
    ansicht = LeseAnsicht()
    ansicht.show()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG, "2026-09-21", "Text")

    empfangen = []
    ansicht.bearbeiten_angefordert.connect(lambda typ, zeitraum: empfangen.append((typ, zeitraum)))
    ansicht.bearbeiten_knopf.setFocus()
    qtbot.keyClick(ansicht.bearbeiten_knopf, Qt.Key.Key_Return)
    assert empfangen == [(EintragTyp.TAG, "2026-09-21")]
