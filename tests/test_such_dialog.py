"""Tests für ui/such_dialog.py."""
from __future__ import annotations

from ui.such_dialog import SuchDialog


def test_suche_mit_begriff_wird_akzeptiert(qtbot):
    dialog = SuchDialog()
    qtbot.addWidget(dialog)
    dialog.suchbegriff_feld.setText("Urlaub")
    dialog._suchen()
    assert dialog.suchbegriff == "Urlaub"
    assert dialog.result() == dialog.DialogCode.Accepted


def test_leerer_suchbegriff_zeigt_fehler(qtbot, monkeypatch):
    dialog = SuchDialog()
    qtbot.addWidget(dialog)

    fehler = []
    monkeypatch.setattr("ui.such_dialog.show_error", lambda parent, text: fehler.append(text))
    dialog._suchen()

    assert fehler == ["Bitte einen Suchbegriff oder eine Frage eingeben."]
    assert dialog.suchbegriff == ""
