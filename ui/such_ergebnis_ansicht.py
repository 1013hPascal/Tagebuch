"""Suchergebnisse: gleiche Darstellung wie die Übersicht, aber typübergreifend
(Abschnitt 7.6 des Konzepts)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit, QVBoxLayout, QWidget

from kern import datum
from kern.modelle import Eintrag, EintragTyp, Suchtreffer

from .announcer import announce
from .common import name_widget

_MELDUNG_ANTWORT_WIRD_GESUCHT = "Antwort wird gesucht …"
_MELDUNG_ANTWORT_GEFUNDEN = "Antwort gefunden."


def _anzeige_text(eintrag: Eintrag, heute: date) -> str:
    if eintrag.typ == EintragTyp.TAG:
        text = datum.tag_anzeigen(eintrag.zeitraum)
        if eintrag.zeitraum == heute.isoformat():
            text += " (heute)"
        return text
    if eintrag.typ == EintragTyp.MONAT:
        return f"Monatsübersicht {datum.monat_anzeigen(eintrag.zeitraum)}"
    return f"Jahresübersicht {datum.jahr_anzeigen(eintrag.zeitraum)}"


class SuchErgebnisAnsicht(QWidget):
    """Liste plus Vorschau der Treffer. Aktivieren folgt denselben Regeln wie die Übersicht."""

    eintrag_oeffnen_editor = Signal(object, object, bool)
    eintrag_oeffnen_leseansicht = Signal(object, str)
    zurueck = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.ki_antwort = QPlainTextEdit()
        self.ki_antwort.setReadOnly(True)
        name_widget(self.ki_antwort, "KI-Antwort")
        self.ki_antwort.setVisible(False)

        self.liste = QListWidget()
        name_widget(self.liste, "Suchergebnisse")
        self.liste.currentItemChanged.connect(self._auswahl_geaendert)
        self.liste.itemActivated.connect(self._eintrag_aktivieren)

        self.vorschau = QPlainTextEdit()
        self.vorschau.setReadOnly(True)
        name_widget(self.vorschau, "Vorschau")

        treffer_layout = QHBoxLayout()
        treffer_layout.addWidget(self.liste, 1)
        treffer_layout.addWidget(self.vorschau, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ki_antwort)
        layout.addLayout(treffer_layout, 1)

        QWidget.setTabOrder(self.ki_antwort, self.liste)
        QWidget.setTabOrder(self.liste, self.vorschau)

        verlassen_kuerzel = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        verlassen_kuerzel.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        verlassen_kuerzel.activated.connect(self.zurueck.emit)

    def anzeigen(self, suchbegriff: str, treffer: list[Suchtreffer]) -> None:
        heute = date.today()

        self.ki_antwort.setVisible(False)
        self.ki_antwort.setPlainText("")

        self.liste.blockSignals(True)
        self.liste.clear()

        kopf_text = (
            f"Suchergebnisse für „{suchbegriff}“: {len(treffer)} Treffer"
            if treffer
            else f"Keine Treffer für „{suchbegriff}“"
        )
        kopf = QListWidgetItem(kopf_text)
        kopf.setData(Qt.ItemDataRole.UserRole, None)
        self.liste.addItem(kopf)

        for eintrag_treffer in treffer:
            item = QListWidgetItem(_anzeige_text(eintrag_treffer.eintrag, heute))
            item.setData(
                Qt.ItemDataRole.UserRole,
                (eintrag_treffer.eintrag.typ, eintrag_treffer.eintrag.zeitraum),
            )
            item.setData(Qt.ItemDataRole.UserRole + 1, eintrag_treffer)
            self.liste.addItem(item)

        self.liste.blockSignals(False)
        self.liste.setCurrentRow(0)

    def fokus_liste(self) -> None:
        self.liste.setFocus()

    def _auswahl_geaendert(self, aktuell: QListWidgetItem | None, _vorherig: QListWidgetItem | None) -> None:
        if aktuell is None:
            self.vorschau.setPlainText("")
            return
        treffer: Suchtreffer | None = aktuell.data(Qt.ItemDataRole.UserRole + 1)
        if treffer is None:
            self.vorschau.setPlainText("")
            return
        basis = treffer.eintrag.stichpunkte or "Noch keine Zusammenfassung vorhanden."
        self.vorschau.setPlainText(f"{basis}\n\n{treffer.ausschnitt}")

    def _eintrag_aktivieren(self, item: QListWidgetItem) -> None:
        daten = item.data(Qt.ItemDataRole.UserRole)
        if daten is None:
            return
        typ, zeitraum = daten
        heute = date.today()

        if typ == EintragTyp.TAG and zeitraum == heute.isoformat():
            treffer: Suchtreffer = item.data(Qt.ItemDataRole.UserRole + 1)
            self.eintrag_oeffnen_editor.emit(EintragTyp.TAG, treffer.eintrag, True)
            return

        self.eintrag_oeffnen_leseansicht.emit(typ, zeitraum)

    # ------------------------------------------------------------------
    # KI-Antwort auf eine Frage (Abschnitt 7.6)
    # ------------------------------------------------------------------

    def frage_beantwortung_starten(self) -> None:
        self.ki_antwort.setVisible(True)
        self.ki_antwort.setPlainText(_MELDUNG_ANTWORT_WIRD_GESUCHT)
        announce(_MELDUNG_ANTWORT_WIRD_GESUCHT)

    def frage_beantwortet(self, antwort: str) -> None:
        self.ki_antwort.setVisible(True)
        self.ki_antwort.setPlainText(antwort)
        self.ki_antwort.setFocus()
        announce(_MELDUNG_ANTWORT_GEFUNDEN)

    def frage_fehlgeschlagen(self, fehlertext: str) -> None:
        self.ki_antwort.setVisible(True)
        self.ki_antwort.setPlainText(fehlertext)
        announce(fehlertext)
