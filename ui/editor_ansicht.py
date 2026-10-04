"""Editor: neuen Eintrag schreiben oder einen vorhandenen bearbeiten
(Abschnitt 7.3 und 7.5 des Konzepts).

Der Spracheingabe-Knopf aus Abschnitt 7.3 ist nur sichtbar, wenn der Editor
„mit Spracheingabe“ geöffnet wird (heutiger Tag / neue Einträge, Annahme A2).
Beim Bearbeiten vergangener Einträge (Abschnitt 7.5) bleibt er ausgeblendet
und aus der Tab-Reihenfolge ausgenommen.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from kern import datum
from kern.config import Config
from kern.datum import DatumFehler
from kern.modelle import Eintrag, EintragTyp
from kern.speicher import Speicher
from sprache import umwandlung
from sprache.aufnahme import Aufnahme, AufnahmeFehler

from .announcer import announce
from .common import JaNeinAbbrechen, PlainEdit, confirm_ja_abbrechen, frage_ja_nein_abbrechen, name_widget, show_error
from .workers import Task

_LABEL = {EintragTyp.TAG: "Datum", EintragTyp.MONAT: "Monat", EintragTyp.JAHR: "Jahr"}
_PARSEN = {
    EintragTyp.TAG: datum.tag_parsen,
    EintragTyp.MONAT: datum.monat_parsen,
    EintragTyp.JAHR: datum.jahr_parsen,
}

_KNOPF_BEREIT = "Ich muss dir was erzählen"
_KNOPF_AUFNAHME_LAEUFT = "Aufnahme beenden"
_KNOPF_WIRD_UMGEWANDELT = "Wird umgewandelt …"
_MELDUNG_BEARBEITUNG_LAEUFT = "Bearbeitung läuft."
_MELDUNG_FERTIG_TRANSKRIBIERT = "Fertig transkribiert."

# Grosszügig bemessen: Whisper "small" transkribiert auf der CPU langsamer als Echtzeit, bei
# einer langen Aufnahme (bis zu max_aufnahme_sekunden) darf das Warten beim Beenden nicht zu
# früh aufgeben (siehe ki/ollama_client.WARTE_TIMEOUT_MS für dieselbe Überlegung bei Ollama).
_UMWANDLUNG_WARTE_TIMEOUT_MS = 180_000


def _heutiger_feldtext(typ: EintragTyp, heute: date) -> str:
    if typ == EintragTyp.TAG:
        return f"{heute.day:02d}.{heute.month:02d}.{heute.year:04d}"
    if typ == EintragTyp.MONAT:
        return f"{heute.month:02d}.{heute.year:04d}"
    return f"{heute.year:04d}"


def _zeitraum_als_feldtext(typ: EintragTyp, zeitraum: str) -> str:
    if typ == EintragTyp.TAG:
        jahr, monat, tag = zeitraum.split("-")
        return f"{tag}.{monat}.{jahr}"
    if typ == EintragTyp.MONAT:
        jahr, monat = zeitraum.split("-")
        return f"{monat}.{jahr}"
    return zeitraum


class EditorAnsicht(QWidget):
    """Ein Editor für Tages-, Monats- und Jahreseinträge."""

    gespeichert = Signal(object, str)  # (EintragTyp, neuer/aktueller zeitraum)
    abgebrochen = Signal()
    status_geaendert = Signal(str)

    def __init__(
        self,
        speicher: Speicher,
        schluessel_holen: Callable[[], bytes],
        config: Config,
        parent: QWidget | None = None,
        *,
        aufnahme_klasse: type = Aufnahme,
        transkribieren_fn: Callable[..., str] = umwandlung.transkribieren,
    ) -> None:
        super().__init__(parent)
        self.speicher = speicher
        self._schluessel_holen = schluessel_holen
        self._config = config
        self._aufnahme_klasse = aufnahme_klasse
        self._transkribieren_fn = transkribieren_fn

        self._typ = EintragTyp.TAG
        self._urspruenglicher_zeitraum: str | None = None
        self._unveraendert_datum = ""
        self._unveraendert_text = ""

        self._aufnahme: Aufnahme | None = None
        self._umwandlungs_task: Task | None = None
        self._aufnahme_timer = QTimer(self)
        self._aufnahme_timer.setInterval(500)
        self._aufnahme_timer.timeout.connect(self._aufnahme_pruefen)

        self.datum_label = QLabel("Datum")
        self.datum_feld = QLineEdit()
        self.datum_label.setBuddy(self.datum_feld)
        self.datum_feld.returnPressed.connect(self._speichern)

        label_text = QLabel("Was geschah")
        self.text_feld = PlainEdit()
        label_text.setBuddy(self.text_feld)
        name_widget(self.text_feld, "Was geschah")

        self.sprache_knopf = QPushButton(_KNOPF_BEREIT)
        self.sprache_knopf.clicked.connect(self._sprache_knopf_geklickt)
        self.sprache_knopf.setVisible(False)

        self.speichern_knopf = QPushButton("Speichern")
        self.speichern_knopf.setDefault(True)  # macht den Knopf per Enter bedienbar, sobald er fokussiert ist
        self.speichern_knopf.clicked.connect(self._speichern)

        speichern_kuerzel = QShortcut(QKeySequence("Ctrl+S"), self)
        speichern_kuerzel.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        speichern_kuerzel.activated.connect(self._speichern)

        verlassen_kuerzel = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        verlassen_kuerzel.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        verlassen_kuerzel.activated.connect(self._pruefen_und_verlassen)

        layout = QVBoxLayout(self)
        layout.addWidget(self.datum_label)
        layout.addWidget(self.datum_feld)
        layout.addWidget(label_text)
        layout.addWidget(self.text_feld, 1)
        layout.addWidget(self.sprache_knopf)
        layout.addWidget(self.speichern_knopf)

        self._tab_reihenfolge_setzen(mit_spracheingabe=False)

    def oeffnen(self, typ: EintragTyp, eintrag: Eintrag | None, *, mit_spracheingabe: bool, heute: date) -> None:
        self._typ = typ
        self._urspruenglicher_zeitraum = eintrag.zeitraum if eintrag is not None else None
        self._sprache_zuruecksetzen()

        beschriftung = _LABEL[typ]
        self.datum_label.setText(beschriftung)
        name_widget(self.datum_feld, beschriftung)

        if eintrag is None:
            self.datum_feld.setText(_heutiger_feldtext(typ, heute))
            self.text_feld.setPlainText("")
        else:
            self.datum_feld.setText(_zeitraum_als_feldtext(typ, eintrag.zeitraum))
            self.text_feld.setPlainText(eintrag.text)

        self._unveraendert_datum = self.datum_feld.text()
        self._unveraendert_text = self.text_feld.toPlainText()

        cursor = self.text_feld.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End if mit_spracheingabe else QTextCursor.MoveOperation.Start
        )
        self.text_feld.setTextCursor(cursor)

        self.sprache_knopf.setVisible(mit_spracheingabe)
        self._tab_reihenfolge_setzen(mit_spracheingabe=mit_spracheingabe)

    def fokus_text_feld(self) -> None:
        self.text_feld.setFocus()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt-Signatur)
        self._sprache_zuruecksetzen()
        super().hideEvent(event)

    def _tab_reihenfolge_setzen(self, *, mit_spracheingabe: bool) -> None:
        QWidget.setTabOrder(self.datum_feld, self.text_feld)
        if mit_spracheingabe:
            QWidget.setTabOrder(self.text_feld, self.sprache_knopf)
            QWidget.setTabOrder(self.sprache_knopf, self.speichern_knopf)
        else:
            QWidget.setTabOrder(self.text_feld, self.speichern_knopf)
        QWidget.setTabOrder(self.speichern_knopf, self.datum_feld)

    def _hat_aenderungen(self) -> bool:
        return (
            self.datum_feld.text() != self._unveraendert_datum
            or self.text_feld.toPlainText() != self._unveraendert_text
        )

    def _pruefen_und_verlassen(self) -> None:
        if not self._hat_aenderungen():
            self.abgebrochen.emit()
            return
        antwort = frage_ja_nein_abbrechen(self, "Änderungen speichern?", "Änderungen speichern?")
        if antwort == JaNeinAbbrechen.JA:
            self._speichern()
        elif antwort == JaNeinAbbrechen.NEIN:
            self.abgebrochen.emit()
        # bei Abbrechen: im Editor bleiben

    def _speichern(self) -> None:
        parsen = _PARSEN[self._typ]
        try:
            zeitraum = parsen(self.datum_feld.text(), date.today())
        except DatumFehler as exc:
            show_error(self, exc.nachricht)
            self.datum_feld.setFocus()
            return

        text = self.text_feld.toPlainText()
        if not text.strip():
            show_error(self, "Es gibt noch nichts zu speichern.")
            return

        schluessel = self._schluessel_holen()
        ist_gleicher_eintrag = zeitraum == self._urspruenglicher_zeitraum
        ziel_vorhanden = (
            None if ist_gleicher_eintrag else self.speicher.eintrag_laden(schluessel, self._typ, zeitraum)
        )

        if ziel_vorhanden is not None:
            frage = (
                "Für diesen Tag gibt es schon einen Eintrag. Text dort anhängen?"
                if self._urspruenglicher_zeitraum is None
                else "Dort gibt es schon einen Eintrag. Text anhängen?"
            )
            if not confirm_ja_abbrechen(self, "Eintrag vorhanden", frage):
                return
            self.speicher.eintrag_speichern(schluessel, self._typ, zeitraum, text, anhaengen=True)
            if self._urspruenglicher_zeitraum is not None:
                self.speicher.eintrag_loeschen(self._typ, self._urspruenglicher_zeitraum)
        else:
            self.speicher.eintrag_speichern(schluessel, self._typ, zeitraum, text, anhaengen=False)
            if self._urspruenglicher_zeitraum is not None and self._urspruenglicher_zeitraum != zeitraum:
                self.speicher.eintrag_loeschen(self._typ, self._urspruenglicher_zeitraum)

        if self._typ in (EintragTyp.MONAT, EintragTyp.JAHR):
            # Manuell geschriebene/bearbeitete Übersichten werden nie automatisch überschrieben
            # (Abschnitt 9.4), außer über „Zusammenfassung neu erstellen“.
            self.speicher.manuell_bearbeitet_setzen(self._typ, zeitraum, True)

        self.gespeichert.emit(self._typ, zeitraum)

    # ------------------------------------------------------------------
    # Spracheingabe (Abschnitt 7.3)
    # ------------------------------------------------------------------

    def _sprache_zuruecksetzen(self) -> None:
        """Bricht eine laufende Aufnahme/Umwandlung ab, z. B. beim Verlassen der Ansicht."""
        self._aufnahme_timer.stop()
        if self._aufnahme is not None:
            try:
                self._aufnahme.stop()
            except Exception:
                pass
            self._aufnahme = None
        if self._umwandlungs_task is not None:
            self._umwandlungs_task.cancel()
            self._umwandlungs_task = None
        self.sprache_knopf.setText(_KNOPF_BEREIT)

    def hintergrund_abbrechen_und_warten(self, timeout_ms: int = _UMWANDLUNG_WARTE_TIMEOUT_MS) -> None:
        """Bricht eine laufende Aufnahme/Umwandlung ab und wartet, bis der Hintergrund-Thread
        wirklich beendet ist. Wichtig beim Beenden des Programms: Ein QThread darf nicht
        zerstört werden, während er noch läuft (das stürzt den Prozess ab). Für normale
        Navigation (z. B. Escape) ist das zu langsam - dafür reicht `_sprache_zuruecksetzen`."""
        task = self._umwandlungs_task
        self._sprache_zuruecksetzen()
        if task is not None:
            task.wait(timeout_ms)

    def _sprache_knopf_geklickt(self) -> None:
        if self._umwandlungs_task is not None:
            return  # Umwandlung läuft noch - weitere Klicks ignorieren, Knopf bleibt fokussierbar
        if self._aufnahme is None:
            self._aufnahme_starten()
        else:
            self._aufnahme_beenden()

    def _aufnahme_starten(self) -> None:
        aufnahme = self._aufnahme_klasse(self._config.max_aufnahme_sekunden)
        try:
            aufnahme.start()
        except AufnahmeFehler as exc:
            show_error(self, str(exc))
            return
        self._aufnahme = aufnahme
        self.sprache_knopf.setText(_KNOPF_AUFNAHME_LAEUFT)
        self._aufnahme_timer.start()
        self.status_geaendert.emit("Aufnahme läuft")
        announce("Aufnahme läuft")

    def _aufnahme_pruefen(self) -> None:
        if self._aufnahme is not None and self._aufnahme.ist_voll():
            self._aufnahme_beenden()

    def _aufnahme_beenden(self) -> None:
        if self._aufnahme is None:
            return
        self._aufnahme_timer.stop()
        audio = self._aufnahme.stop()
        self._aufnahme = None

        # Der Knopf bleibt bewusst aktiviert (nicht setEnabled(False)): Ein deaktiviertes
        # Widget verliert in Qt automatisch den Fokus. Weitere Klicks während der
        # Umwandlung werden stattdessen in _sprache_knopf_geklickt() ignoriert.
        self.sprache_knopf.setText(_KNOPF_WIRD_UMGEWANDELT)
        self.status_geaendert.emit(_MELDUNG_BEARBEITUNG_LAEUFT)
        announce(_MELDUNG_BEARBEITUNG_LAEUFT)

        modell_name = self._config.whisper_modell
        sprache = self._config.whisper_sprache
        transkribieren_fn = self._transkribieren_fn

        def arbeit(_task: Task) -> str:
            return transkribieren_fn(audio, modell_name=modell_name, sprache=sprache)

        task = Task(arbeit, self)
        task.result.connect(self._umwandlung_fertig)
        task.error.connect(self._umwandlung_fehlgeschlagen)
        task.cancelled.connect(self._umwandlung_abgebrochen)
        task.finished.connect(task.deleteLater)
        self._umwandlungs_task = task
        task.start()

    def _umwandlung_fertig(self, text: str) -> None:
        self._umwandlungs_task = None
        self.sprache_knopf.setText(_KNOPF_BEREIT)

        if not text.strip():
            self.sprache_knopf.setFocus()
            self.status_geaendert.emit("Es wurde nichts verstanden.")
            announce("Es wurde nichts verstanden.")
            return

        vorhandener_text = self.text_feld.toPlainText()
        trenner = "\n\n" if vorhandener_text else ""
        einfuege_position = len(vorhandener_text) + len(trenner)

        cursor = self.text_feld.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(trenner + text)
        # Cursor an den Anfang der neu eingefügten Stelle setzen (nicht ans Ende dahinter),
        # damit man beim Weiterlesen/-schreiben genau dort ansetzt, wo der Text eingefügt wurde.
        cursor.setPosition(einfuege_position)
        self.text_feld.setTextCursor(cursor)
        self.text_feld.setFocus()
        self.text_feld.ensureCursorVisible()

        self.status_geaendert.emit(_MELDUNG_FERTIG_TRANSKRIBIERT)
        announce(_MELDUNG_FERTIG_TRANSKRIBIERT)

    def _umwandlung_fehlgeschlagen(self, fehlertext: str) -> None:
        self._umwandlungs_task = None
        self.sprache_knopf.setText(_KNOPF_BEREIT)
        show_error(self, fehlertext)

    def _umwandlung_abgebrochen(self) -> None:
        self._umwandlungs_task = None
        self.sprache_knopf.setText(_KNOPF_BEREIT)
