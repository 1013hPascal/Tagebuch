"""Tests für ui/editor_ansicht.py (Abschnitt 7.3, 7.5 und 8 des Konzepts)."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from kern.config import Config
from kern.modelle import EintragTyp
from sprache.aufnahme import AufnahmeFehler
from ui.common import JaNeinAbbrechen
from ui.editor_ansicht import EditorAnsicht

HEUTE = date(2026, 9, 22)


def _bauen(speicher, schluessel):
    return EditorAnsicht(speicher, lambda: schluessel, Config())


class FakeAufnahme:
    """Ersetzt sprache.aufnahme.Aufnahme in Tests, ohne echtes Mikrofon."""

    def __init__(self, max_sekunden: int) -> None:
        self.max_sekunden = max_sekunden
        self.gestartet = False
        self.gestoppt = False

    def start(self) -> None:
        self.gestartet = True

    def ist_voll(self) -> bool:
        return False

    def stop(self) -> np.ndarray:
        self.gestoppt = True
        return np.array([0.1, 0.2], dtype=np.float32)


class FehlerhafteAufnahme:
    """Simuliert ein fehlendes Mikrofon."""

    def __init__(self, max_sekunden: int) -> None:
        pass

    def start(self) -> None:
        raise AufnahmeFehler("Kein Mikrofon verfügbar: Testfehler")


def test_neuer_tageseintrag_wird_gespeichert(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    assert editor.datum_feld.text() == "22.09.2026"

    editor.text_feld.setPlainText("Heute ist etwas passiert.")
    empfangen = []
    editor.gespeichert.connect(lambda typ, zeitraum: empfangen.append((typ, zeitraum)))
    editor._speichern()

    assert empfangen == [(EintragTyp.TAG, "2026-09-22")]
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.text == "Heute ist etwas passiert."


def test_leerer_text_wird_nicht_gespeichert(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    fehler = []
    monkeypatch.setattr("ui.editor_ansicht.show_error", lambda parent, text: fehler.append(text))
    editor._speichern()
    assert fehler == ["Es gibt noch nichts zu speichern."]
    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22") is None


def test_ungueltiges_datum_zeigt_fehler(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.datum_feld.setText("31.02.2026")
    editor.text_feld.setPlainText("Text")

    fehler = []
    monkeypatch.setattr("ui.editor_ansicht.show_error", lambda parent, text: fehler.append(text))
    editor._speichern()
    assert len(fehler) == 1
    assert "gibt es nicht" in fehler[0]


def test_datum_in_der_zukunft_zeigt_fehler(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    morgen = date.today() + timedelta(days=1)
    editor.datum_feld.setText(morgen.strftime("%d.%m.%Y"))
    editor.text_feld.setPlainText("Text")

    fehler = []
    monkeypatch.setattr("ui.editor_ansicht.show_error", lambda parent, text: fehler.append(text))
    editor._speichern()
    assert fehler == ["Das Datum darf nicht in der Zukunft liegen."]


def test_anhaengen_bei_vorhandenem_zieleintrag(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Alter Text")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.datum_feld.setText("20.09.2026")
    editor.text_feld.setPlainText("Neuer Text")

    monkeypatch.setattr("ui.editor_ansicht.confirm_ja_abbrechen", lambda *a, **k: True)
    editor._speichern()

    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20")
    assert eintrag.text == "Alter Text\n\nNeuer Text"


def test_anhaengen_abgebrochen_veraendert_nichts(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Alter Text")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.datum_feld.setText("20.09.2026")
    editor.text_feld.setPlainText("Neuer Text")

    monkeypatch.setattr("ui.editor_ansicht.confirm_ja_abbrechen", lambda *a, **k: False)
    empfangen = []
    editor.gespeichert.connect(lambda *a: empfangen.append(a))
    editor._speichern()

    assert empfangen == []
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20")
    assert eintrag.text == "Alter Text"


def test_bearbeiten_verschiebt_eintrag_auf_neues_datum(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20")

    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, eintrag, mit_spracheingabe=False, heute=HEUTE)
    editor.datum_feld.setText("21.09.2026")
    editor._speichern()

    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20") is None
    verschoben = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-21")
    assert verschoben.text == "Text"


def test_bearbeiten_gleiches_datum_ueberschreibt_ohne_anhaengen(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Alt")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20")

    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, eintrag, mit_spracheingabe=False, heute=HEUTE)
    editor.text_feld.setPlainText("Ersetzt")
    editor._speichern()

    aktualisiert = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-20")
    assert aktualisiert.text == "Ersetzt"


def test_monat_editor_verwendet_monat_format(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.MONAT, None, mit_spracheingabe=False, heute=HEUTE)
    assert editor.datum_feld.text() == "09.2026"
    assert editor.datum_label.text() == "Monat"

    editor.text_feld.setPlainText("Zusammenfassung des Monats.")
    editor._speichern()
    assert speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-09") is not None


def test_cursor_am_ende_bei_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, eintrag, mit_spracheingabe=True, heute=HEUTE)
    assert editor.text_feld.textCursor().position() == len("Text")


def test_cursor_am_anfang_ohne_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, eintrag, mit_spracheingabe=False, heute=HEUTE)
    assert editor.text_feld.textCursor().position() == 0


def test_unveraendert_verlassen_ohne_rueckfrage(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    abgebrochen = []
    editor.abgebrochen.connect(lambda: abgebrochen.append(True))
    editor._pruefen_und_verlassen()
    assert abgebrochen == [True]


def test_veraendert_verlassen_mit_nein_verwirft_aenderungen(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Etwas Neues")

    monkeypatch.setattr(
        "ui.editor_ansicht.frage_ja_nein_abbrechen", lambda *a, **k: JaNeinAbbrechen.NEIN
    )
    abgebrochen = []
    editor.abgebrochen.connect(lambda: abgebrochen.append(True))
    editor._pruefen_und_verlassen()

    assert abgebrochen == [True]
    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22") is None


def test_veraendert_verlassen_mit_ja_speichert(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Etwas Neues")

    monkeypatch.setattr(
        "ui.editor_ansicht.frage_ja_nein_abbrechen", lambda *a, **k: JaNeinAbbrechen.JA
    )
    gespeichert = []
    editor.gespeichert.connect(lambda *a: gespeichert.append(a))
    editor._pruefen_und_verlassen()

    assert gespeichert == [(EintragTyp.TAG, "2026-09-22")]


def test_veraendert_verlassen_mit_abbrechen_bleibt_im_editor(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Etwas Neues")

    monkeypatch.setattr(
        "ui.editor_ansicht.frage_ja_nein_abbrechen", lambda *a, **k: JaNeinAbbrechen.ABBRECHEN
    )
    abgebrochen = []
    editor.abgebrochen.connect(lambda: abgebrochen.append(True))
    editor._pruefen_und_verlassen()

    assert abgebrochen == []
    assert editor.text_feld.toPlainText() == "Etwas Neues"


def test_spracheingabe_knopf_nur_sichtbar_mit_flag(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.show()

    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    assert editor.sprache_knopf.isVisible() is True

    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=False, heute=HEUTE)
    assert editor.sprache_knopf.isVisible() is False


def test_aufnahme_starten_aendert_knopftext_und_status(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = EditorAnsicht(speicher, lambda: schluessel, Config(), aufnahme_klasse=FakeAufnahme)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    status = []
    editor.status_geaendert.connect(status.append)
    editor.sprache_knopf.click()

    assert editor.sprache_knopf.text() == "Aufnahme beenden"
    assert status == ["Aufnahme läuft"]
    assert editor._aufnahme is not None and editor._aufnahme.gestartet is True


def test_kein_mikrofon_zeigt_fehler_und_bleibt_bereit(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    editor = EditorAnsicht(speicher, lambda: schluessel, Config(), aufnahme_klasse=FehlerhafteAufnahme)
    qtbot.addWidget(editor)
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    fehler = []
    monkeypatch.setattr("ui.editor_ansicht.show_error", lambda parent, text: fehler.append(text))
    editor.sprache_knopf.click()

    assert len(fehler) == 1
    assert "Kein Mikrofon" in fehler[0]
    assert editor.sprache_knopf.text() == "Ich muss dir was erzählen"
    assert editor._aufnahme is None


def test_aufnahme_beenden_transkribiert_und_haengt_text_an(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")

    def fake_transkribieren(audio, *, modell_name, sprache):
        return "Erkannter Text"

    editor = EditorAnsicht(
        speicher,
        lambda: schluessel,
        Config(),
        aufnahme_klasse=FakeAufnahme,
        transkribieren_fn=fake_transkribieren,
    )
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Vorhandener Text.")

    status = []
    editor.status_geaendert.connect(status.append)

    editor.sprache_knopf.click()  # Aufnahme starten
    editor.sprache_knopf.click()  # Aufnahme beenden -> Umwandlung im Hintergrund

    assert editor.sprache_knopf.text() == "Wird umgewandelt …"
    # Der Knopf bleibt bewusst aktiviert und fokussierbar (kein setEnabled(False)) -
    # ein deaktiviertes Widget würde in Qt automatisch den Fokus verlieren.
    assert editor.sprache_knopf.isEnabled() is True
    assert status[-1] == "Bearbeitung läuft."

    # Ein weiterer Klick waehrend der Umwandlung wird ignoriert (kein zweiter Task).
    editor.sprache_knopf.click()

    qtbot.waitUntil(lambda: editor._umwandlungs_task is None, timeout=3000)
    assert editor.sprache_knopf.text() == "Ich muss dir was erzählen"
    assert editor.text_feld.toPlainText() == "Vorhandener Text.\n\nErkannter Text"
    assert status[-1] == "Fertig transkribiert."

    # Fokus springt ins Textfeld, an den Anfang der neu eingefuegten Stelle.
    assert editor.text_feld.hasFocus() is True
    einfuege_position = len("Vorhandener Text.\n\n")
    assert editor.text_feld.textCursor().position() == einfuege_position


def test_nichts_verstanden_zeigt_hinweis(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")

    def fake_transkribieren(audio, *, modell_name, sprache):
        return ""

    editor = EditorAnsicht(
        speicher,
        lambda: schluessel,
        Config(),
        aufnahme_klasse=FakeAufnahme,
        transkribieren_fn=fake_transkribieren,
    )
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    status = []
    editor.status_geaendert.connect(status.append)
    editor.sprache_knopf.click()
    editor.sprache_knopf.click()

    qtbot.waitUntil(lambda: editor._umwandlungs_task is None, timeout=3000)
    assert status[-1] == "Es wurde nichts verstanden."
    assert editor.text_feld.toPlainText() == ""
    assert editor.sprache_knopf.hasFocus() is True


def test_verlassen_waehrend_aufnahme_bricht_ab(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = EditorAnsicht(speicher, lambda: schluessel, Config(), aufnahme_klasse=FakeAufnahme)
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.sprache_knopf.click()
    assert editor._aufnahme is not None

    editor.hide()  # wie beim Wechsel der QStackedWidget-Seite

    assert editor._aufnahme is None
    assert editor.sprache_knopf.text() == "Ich muss dir was erzählen"


def test_enter_im_textfeld_erzeugt_zeilenumbruch(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)

    editor.text_feld.setFocus()
    QTest.keyClicks(editor.text_feld, "erste zeile")
    QTest.keyClick(editor.text_feld, Qt.Key.Key_Return)
    QTest.keyClicks(editor.text_feld, "zweite zeile")

    assert editor.text_feld.toPlainText() == "erste zeile\nzweite zeile"


def test_enter_im_datumsfeld_speichert(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Ein Text.")

    gespeichert = []
    editor.gespeichert.connect(lambda *a: gespeichert.append(a))
    editor.datum_feld.setFocus()
    QTest.keyClick(editor.datum_feld, Qt.Key.Key_Return)

    assert gespeichert == [(EintragTyp.TAG, "2026-09-22")]


def test_enter_auf_fokussiertem_speichern_knopf_loest_speichern_aus(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    editor = _bauen(speicher, schluessel)
    qtbot.addWidget(editor)
    editor.show()
    editor.oeffnen(EintragTyp.TAG, None, mit_spracheingabe=True, heute=HEUTE)
    editor.text_feld.setPlainText("Ein Text.")

    gespeichert = []
    editor.gespeichert.connect(lambda *a: gespeichert.append(a))
    editor.speichern_knopf.setFocus()
    QTest.keyClick(editor.speichern_knopf, Qt.Key.Key_Return)

    assert gespeichert == [(EintragTyp.TAG, "2026-09-22")]
