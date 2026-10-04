"""Tests für ui/passwort_dialog.py (Abschnitt 5 des Konzepts)."""
from __future__ import annotations

from ui.passwort_dialog import AccountLoeschenDialog, PasswortAendernDialog


def test_passwort_aendern_mit_richtigem_altem_passwort(qtbot, speicher):
    speicher.einrichten("altes-passwort")
    dialog = PasswortAendernDialog(speicher)
    qtbot.addWidget(dialog)

    dialog.altes_passwort.setText("altes-passwort")
    dialog.neues_passwort.setText("neues-passwort")
    dialog.wiederholung.setText("neues-passwort")
    dialog._aendern()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.neuer_schluessel is not None
    assert speicher.anmelden("neues-passwort") == dialog.neuer_schluessel


def test_passwort_aendern_mit_falschem_altem_passwort(qtbot, speicher, monkeypatch):
    speicher.einrichten("richtig")
    dialog = PasswortAendernDialog(speicher)
    qtbot.addWidget(dialog)

    fehler = []
    monkeypatch.setattr("ui.passwort_dialog.show_error", lambda parent, text: fehler.append(text))
    dialog.altes_passwort.setText("falsch")
    dialog.neues_passwort.setText("neu")
    dialog.wiederholung.setText("neu")
    dialog._aendern()

    assert fehler == ["Das alte Passwort ist nicht richtig."]
    assert dialog.neuer_schluessel is None
    assert dialog.altes_passwort.text() == ""


def test_passwort_aendern_mit_nicht_uebereinstimmenden_neuen_passwoertern(qtbot, speicher, monkeypatch):
    speicher.einrichten("altes-passwort")
    dialog = PasswortAendernDialog(speicher)
    qtbot.addWidget(dialog)

    fehler = []
    monkeypatch.setattr("ui.passwort_dialog.show_error", lambda parent, text: fehler.append(text))
    dialog.altes_passwort.setText("altes-passwort")
    dialog.neues_passwort.setText("eins")
    dialog.wiederholung.setText("zwei")
    dialog._aendern()

    assert fehler == ["Die Passwörter stimmen nicht überein."]
    assert dialog.neuer_schluessel is None
    assert dialog.neues_passwort.text() == ""
    assert dialog.wiederholung.text() == ""


def test_account_loeschen_mit_richtigem_passwort(qtbot, speicher):
    speicher.einrichten("mein-passwort")
    pfad = speicher.pfad
    dialog = AccountLoeschenDialog(speicher)
    qtbot.addWidget(dialog)

    dialog.passwort.setText("mein-passwort")
    dialog._loeschen()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert not pfad.exists()


def test_account_loeschen_mit_falschem_passwort(qtbot, speicher, monkeypatch):
    speicher.einrichten("mein-passwort")
    pfad = speicher.pfad
    dialog = AccountLoeschenDialog(speicher)
    qtbot.addWidget(dialog)

    fehler = []
    monkeypatch.setattr("ui.passwort_dialog.show_error", lambda parent, text: fehler.append(text))
    dialog.passwort.setText("falsch")
    dialog._loeschen()

    assert fehler == ["Das Passwort ist nicht richtig."]
    assert dialog.result() != dialog.DialogCode.Accepted
    assert pfad.exists()
