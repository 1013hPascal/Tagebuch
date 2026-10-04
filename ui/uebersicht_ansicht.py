"""Übersicht: Liste plus Vorschau, für Tage, Monate und Jahre gleich aufgebaut
(Abschnitt 7.2 des Konzepts). Ein Widget bedient alle drei Varianten."""
from __future__ import annotations

from datetime import date
from typing import Callable

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit, QWidget

from kern import datum
from kern.speicher import Speicher
from kern.modelle import EintragTyp

from .common import confirm, name_widget
from .menus import AccessibleMenu

_OBERSTER_TEXT = {
    EintragTyp.TAG: "Was ich zu erzählen habe",
    EintragTyp.MONAT: "Neue Monatsübersicht schreiben",
    EintragTyp.JAHR: "Neue Jahresübersicht schreiben",
}
_OBERSTER_HINWEIS = {
    EintragTyp.TAG: "Neuen Eintrag für heute schreiben.",
    EintragTyp.MONAT: "Neue Monatsübersicht schreiben.",
    EintragTyp.JAHR: "Neue Jahresübersicht schreiben.",
}
_LISTEN_NAME = {
    EintragTyp.TAG: "Tagesübersicht",
    EintragTyp.MONAT: "Monatsübersicht",
    EintragTyp.JAHR: "Jahresübersicht",
}


def _anzeige_text(typ: EintragTyp, zeitraum: str, heute: date) -> str:
    if typ == EintragTyp.TAG:
        text = datum.tag_anzeigen(zeitraum)
        if zeitraum == heute.isoformat():
            text += " (heute)"
        return text
    if typ == EintragTyp.MONAT:
        return datum.monat_anzeigen(zeitraum)
    return datum.jahr_anzeigen(zeitraum)


def _kurzer_zeitraum_text(typ: EintragTyp, zeitraum: str) -> str:
    if typ == EintragTyp.TAG:
        jahr, monat, tag = zeitraum.split("-")
        return f"vom {tag}.{monat}.{jahr}"
    if typ == EintragTyp.MONAT:
        return datum.monat_anzeigen(zeitraum)
    return datum.jahr_anzeigen(zeitraum)


class UebersichtAnsicht(QWidget):
    """Zeigt die Liste eines Zeitraum-Typs (Tag/Monat/Jahr) mit Vorschau.

    `eintrag_oeffnen_editor` liefert (typ, Eintrag-oder-None, mit_spracheingabe).
    `eintrag_oeffnen_leseansicht` liefert (typ, zeitraum).
    """

    eintrag_oeffnen_editor = Signal(object, object, bool)
    eintrag_oeffnen_leseansicht = Signal(object, str)
    zusammenfassung_neu_erstellen_angefordert = Signal(object, str)

    def __init__(
        self,
        speicher: Speicher,
        schluessel_holen: Callable[[], bytes],
        parent: QWidget | None = None,
        *,
        ist_in_bearbeitung: Callable[[EintragTyp, str], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self.speicher = speicher
        self._schluessel_holen = schluessel_holen
        self._ist_in_bearbeitung = ist_in_bearbeitung or (lambda _typ, _zeitraum: False)
        self._typ = EintragTyp.TAG

        self.liste = QListWidget()
        self.liste.currentItemChanged.connect(self._auswahl_geaendert)
        self.liste.itemActivated.connect(self._eintrag_aktivieren)
        self.liste.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._kontextmenu)
        self.liste.installEventFilter(self)

        self.vorschau = QPlainTextEdit()
        self.vorschau.setReadOnly(True)
        name_widget(self.vorschau, "Vorschau")

        layout = QHBoxLayout(self)
        layout.addWidget(self.liste, 1)
        layout.addWidget(self.vorschau, 1)

        QWidget.setTabOrder(self.liste, self.vorschau)

    def anzeigen(self, typ: EintragTyp) -> None:
        self._typ = typ
        name_widget(self.liste, _LISTEN_NAME[typ])

        heute = date.today()
        schluessel = self._schluessel_holen()

        self.liste.blockSignals(True)
        self.liste.clear()

        oberster = QListWidgetItem(_OBERSTER_TEXT[typ])
        oberster.setData(Qt.ItemDataRole.UserRole, None)
        self.liste.addItem(oberster)

        for eintrag in self.speicher.eintraege_liste(schluessel, typ):
            item = QListWidgetItem(_anzeige_text(typ, eintrag.zeitraum, heute))
            item.setData(Qt.ItemDataRole.UserRole, eintrag.zeitraum)
            self.liste.addItem(item)

        self.liste.blockSignals(False)
        self.liste.setCurrentRow(0)

    def auswaehlen(self, zeitraum: str) -> None:
        for zeile in range(self.liste.count()):
            item = self.liste.item(zeile)
            if item.data(Qt.ItemDataRole.UserRole) == zeitraum:
                self.liste.setCurrentRow(zeile)
                return

    def aktuelle_auswahl(self) -> str | None:
        item = self.liste.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def aktualisiere_vorschau(self) -> None:
        self._auswahl_geaendert(self.liste.currentItem(), None)

    def fokus_liste(self) -> None:
        self.liste.setFocus()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt-Signatur)
        if (
            obj is self.liste
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Delete
        ):
            item = self.liste.currentItem()
            if item is not None and item.data(Qt.ItemDataRole.UserRole) is not None:
                self._eintrag_loeschen(item)
            return True
        return super().eventFilter(obj, event)

    def _auswahl_geaendert(self, aktuell: QListWidgetItem | None, _vorherig: QListWidgetItem | None) -> None:
        if aktuell is None:
            self.vorschau.setPlainText("")
            return
        zeitraum = aktuell.data(Qt.ItemDataRole.UserRole)
        if zeitraum is None:
            self.vorschau.setPlainText(_OBERSTER_HINWEIS[self._typ])
            return
        eintrag = self.speicher.eintrag_laden(self._schluessel_holen(), self._typ, zeitraum)
        if eintrag is None:
            self.vorschau.setPlainText("")
        elif eintrag.stichpunkte:
            self.vorschau.setPlainText(eintrag.stichpunkte)
        elif self._ist_in_bearbeitung(self._typ, zeitraum):
            self.vorschau.setPlainText("Zusammenfassung wird erstellt …")
        else:
            self.vorschau.setPlainText("Noch keine Zusammenfassung vorhanden.")

    def _eintrag_aktivieren(self, item: QListWidgetItem) -> None:
        zeitraum = item.data(Qt.ItemDataRole.UserRole)
        schluessel = self._schluessel_holen()
        heute = date.today()

        if zeitraum is None:
            if self._typ == EintragTyp.TAG:
                vorhandener = self.speicher.eintrag_laden(schluessel, EintragTyp.TAG, heute.isoformat())
                self.eintrag_oeffnen_editor.emit(EintragTyp.TAG, vorhandener, True)
            else:
                self.eintrag_oeffnen_editor.emit(self._typ, None, False)
            return

        if self._typ == EintragTyp.TAG and zeitraum == heute.isoformat():
            eintrag = self.speicher.eintrag_laden(schluessel, EintragTyp.TAG, zeitraum)
            self.eintrag_oeffnen_editor.emit(EintragTyp.TAG, eintrag, True)
            return

        self.eintrag_oeffnen_leseansicht.emit(self._typ, zeitraum)

    def _kontextmenu(self, pos) -> None:
        item = self.liste.itemAt(pos)
        zeitraum = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if item is None or zeitraum is None:
            return
        menu = AccessibleMenu("Eintrag", self.liste)
        aktion_loeschen = menu.addAction("Eintrag löschen")
        aktion_neu = menu.addAction("Zusammenfassung neu erstellen")
        gewaehlt = menu.exec(self.liste.mapToGlobal(pos))
        if gewaehlt is aktion_loeschen:
            self._eintrag_loeschen(item)
        elif aktion_neu is not None and gewaehlt is aktion_neu:
            self.zusammenfassung_neu_erstellen_angefordert.emit(self._typ, zeitraum)

    def _eintrag_loeschen(self, item: QListWidgetItem) -> None:
        zeitraum = item.data(Qt.ItemDataRole.UserRole)
        anzeige = _kurzer_zeitraum_text(self._typ, zeitraum)
        if not confirm(
            self,
            "Eintrag löschen",
            f"Eintrag {anzeige} wirklich löschen? Das kann nicht rückgängig gemacht werden.",
        ):
            return
        zeile = self.liste.row(item)
        self.speicher.eintrag_loeschen(self._typ, zeitraum)
        self.anzeigen(self._typ)
        naechste_zeile = max(0, min(zeile, self.liste.count() - 1))
        self.liste.setCurrentRow(naechste_zeile)
        self.liste.setFocus()
