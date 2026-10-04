"""Tests für ui/such_ergebnis_ansicht.py (Abschnitt 7.6 des Konzepts)."""
from __future__ import annotations

from datetime import date

from kern.modelle import EintragTyp
from ui.such_ergebnis_ansicht import SuchErgebnisAnsicht


def test_kopfzeile_mit_treffern(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Urlaub")
    treffer = speicher.suchen(schluessel, "Urlaub")

    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Urlaub", treffer)

    assert ansicht.liste.count() == 2
    assert ansicht.liste.item(0).text() == "Suchergebnisse für „Urlaub“: 1 Treffer"


def test_kopfzeile_ohne_treffer(qtbot):
    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Nichtvorhanden", [])

    assert ansicht.liste.count() == 1
    assert ansicht.liste.item(0).text() == "Keine Treffer für „Nichtvorhanden“"


def test_monat_und_jahr_treffer_haben_kennzeichnung(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Urlaub im Monat")
    speicher.eintrag_speichern(schluessel, EintragTyp.JAHR, "2025", "Urlaub im Jahr")
    treffer = speicher.suchen(schluessel, "Urlaub")

    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Urlaub", treffer)

    texte = [ansicht.liste.item(i).text() for i in range(1, ansicht.liste.count())]
    assert "Monatsübersicht August 2026" in texte
    assert "Jahresübersicht 2025" in texte


def test_vorschau_zeigt_stichpunkte_und_ausschnitt(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Ein Urlaub in Italien.")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Urlaub", "hash")
    treffer = speicher.suchen(schluessel, "Urlaub")

    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Urlaub", treffer)
    ansicht.liste.setCurrentRow(1)

    text = ansicht.vorschau.toPlainText()
    assert "- Urlaub" in text
    assert "Italien" in text


def test_aktivieren_heutigen_tag_oeffnet_editor_mit_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    heute = date.today().isoformat()
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, heute, "Urlaub heute")
    treffer = speicher.suchen(schluessel, "Urlaub")

    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Urlaub", treffer)

    empfangen = []
    ansicht.eintrag_oeffnen_editor.connect(lambda typ, eintrag, mit: empfangen.append((typ, eintrag, mit)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(1))

    assert len(empfangen) == 1
    typ, eintrag, mit_spracheingabe = empfangen[0]
    assert typ == EintragTyp.TAG
    assert eintrag.zeitraum == heute
    assert mit_spracheingabe is True


def test_aktivieren_vergangenen_treffer_oeffnet_leseansicht(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Urlaub früher")
    treffer = speicher.suchen(schluessel, "Urlaub")

    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("Urlaub", treffer)

    empfangen = []
    ansicht.eintrag_oeffnen_leseansicht.connect(lambda typ, zeitraum: empfangen.append((typ, zeitraum)))
    ansicht._eintrag_aktivieren(ansicht.liste.item(1))

    assert empfangen == [(EintragTyp.TAG, "2020-01-01")]


def test_frage_beantwortung_starten_zeigt_hinweis(qtbot):
    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)

    ansicht.frage_beantwortung_starten()

    assert ansicht.ki_antwort.isHidden() is False
    assert ansicht.ki_antwort.toPlainText() == "Antwort wird gesucht …"


def test_frage_beantwortet_zeigt_antwort_und_fokussiert(qtbot):
    ansicht = SuchErgebnisAnsicht()
    ansicht.show()
    qtbot.addWidget(ansicht)
    qtbot.wait(50)

    ansicht.frage_beantwortung_starten()
    ansicht.frage_beantwortet("Die Antwort auf die Frage.")

    assert ansicht.ki_antwort.toPlainText() == "Die Antwort auf die Frage."
    assert ansicht.ki_antwort.hasFocus() is True


def test_frage_fehlgeschlagen_zeigt_fehlertext(qtbot):
    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)

    ansicht.frage_beantwortung_starten()
    ansicht.frage_fehlgeschlagen("Ollama ist nicht erreichbar.")

    assert ansicht.ki_antwort.toPlainText() == "Ollama ist nicht erreichbar."


def test_anzeigen_versteckt_vorherige_ki_antwort(qtbot):
    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)

    ansicht.frage_beantwortung_starten()
    ansicht.frage_beantwortet("Alte Antwort.")
    ansicht.anzeigen("Neue Suche", [])

    assert ansicht.ki_antwort.isHidden() is True
    assert ansicht.ki_antwort.toPlainText() == ""


def test_aktivieren_kopfzeile_tut_nichts(qtbot):
    ansicht = SuchErgebnisAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.anzeigen("X", [])

    empfangen = []
    ansicht.eintrag_oeffnen_leseansicht.connect(lambda *a: empfangen.append(a))
    ansicht.eintrag_oeffnen_editor.connect(lambda *a: empfangen.append(a))
    ansicht._eintrag_aktivieren(ansicht.liste.item(0))

    assert empfangen == []
