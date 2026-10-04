"""Tests für ui/uebersicht_ansicht.py (Abschnitt 7.2 des Konzepts)."""
from __future__ import annotations

from datetime import date

from kern.modelle import EintragTyp
from ui.uebersicht_ansicht import UebersichtAnsicht


def _bauen(speicher, schluessel):
    return UebersichtAnsicht(speicher, lambda: schluessel)


def test_oberster_eintrag_ist_immer_vorhanden(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)
    assert ansicht.liste.count() == 1
    assert ansicht.liste.item(0).text() == "Was ich zu erzählen habe"


def test_monat_und_jahr_haben_eigenen_obersten_text(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.MONAT)
    assert ansicht.liste.item(0).text() == "Neue Monatsübersicht schreiben"
    ansicht.anzeigen(EintragTyp.JAHR)
    assert ansicht.liste.item(0).text() == "Neue Jahresübersicht schreiben"


def test_eintraege_neueste_oben_und_heute_markiert(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    heute = date.today().isoformat()
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Alt")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, heute, "Heute")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)
    assert ansicht.liste.count() == 3
    assert "(heute)" in ansicht.liste.item(1).text()
    assert "(heute)" not in ansicht.liste.item(2).text()


def test_vorschau_zeigt_hinweis_ohne_stichpunkte(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Text")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)
    ansicht.liste.setCurrentRow(1)
    assert ansicht.vorschau.toPlainText() == "Noch keine Zusammenfassung vorhanden."


def test_vorschau_zeigt_stichpunkte_wenn_vorhanden(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Text")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "- Ein Punkt", "hash")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)
    ansicht.liste.setCurrentRow(1)
    assert ansicht.vorschau.toPlainText() == "- Ein Punkt"


def test_vorschau_oberster_eintrag_zeigt_hinweistext(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)
    ansicht.liste.setCurrentRow(0)
    assert ansicht.vorschau.toPlainText() == "Neuen Eintrag für heute schreiben."


def test_aktivieren_oberster_eintrag_oeffnet_editor_mit_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    empfangen = []
    ansicht.eintrag_oeffnen_editor.connect(lambda typ, eintrag, mit: empfangen.append((typ, eintrag, mit)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(0))
    assert len(empfangen) == 1
    typ, eintrag, mit_spracheingabe = empfangen[0]
    assert typ == EintragTyp.TAG
    assert eintrag is None
    assert mit_spracheingabe is True


def test_monat_aktivieren_obersten_eintrag_ohne_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.MONAT)

    empfangen = []
    ansicht.eintrag_oeffnen_editor.connect(lambda typ, eintrag, mit: empfangen.append((typ, eintrag, mit)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(0))
    assert empfangen == [(EintragTyp.MONAT, None, False)]


def test_aktivieren_vergangener_tag_oeffnet_leseansicht(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Text")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    empfangen = []
    ansicht.eintrag_oeffnen_leseansicht.connect(lambda typ, zeitraum: empfangen.append((typ, zeitraum)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(1))
    assert empfangen == [(EintragTyp.TAG, "2020-01-01")]


def test_aktivieren_heutigen_tag_oeffnet_editor_mit_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    heute = date.today().isoformat()
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, heute, "Text")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    empfangen = []
    ansicht.eintrag_oeffnen_editor.connect(lambda typ, eintrag, mit: empfangen.append((typ, eintrag, mit)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(1))
    assert len(empfangen) == 1
    typ, eintrag, mit_spracheingabe = empfangen[0]
    assert eintrag is not None and eintrag.zeitraum == heute
    assert mit_spracheingabe is True


def test_eintrag_loeschen_entfernt_ihn_und_setzt_fokus(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Text")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    monkeypatch.setattr("ui.uebersicht_ansicht.confirm", lambda *a, **k: True)
    ansicht.liste.setCurrentRow(1)
    ansicht._eintrag_loeschen(ansicht.liste.item(1))

    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2020-01-01") is None
    assert ansicht.liste.count() == 1


def test_eintrag_loeschen_abgebrochen_behaelt_eintrag(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Text")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    monkeypatch.setattr("ui.uebersicht_ansicht.confirm", lambda *a, **k: False)
    ansicht._eintrag_loeschen(ansicht.liste.item(1))

    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2020-01-01") is not None


def test_auswaehlen_setzt_currentrow(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Alt")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-06-01", "Neu")
    ansicht = _bauen(speicher, schluessel)
    qtbot.addWidget(ansicht)
    ansicht.anzeigen(EintragTyp.TAG)

    ansicht.auswaehlen("2020-01-01")
    assert ansicht.aktuelle_auswahl() == "2020-01-01"
