"""Leseansicht für vergangene Tage, Monate und Jahre (Abschnitt 7.4 des Konzepts)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from kern import datum
from kern.modelle import EintragTyp

from .common import name_widget


def _accessible_name(typ: EintragTyp, zeitraum: str) -> str:
    if typ == EintragTyp.TAG:
        jahr, monat, tag = zeitraum.split("-")
        return f"Eintrag vom {tag}.{monat}.{jahr}"
    if typ == EintragTyp.MONAT:
        return datum.monat_anzeigen(zeitraum)
    return datum.jahr_anzeigen(zeitraum)


class LeseAnsicht(QWidget):
    """Zeigt einen vollständigen, schreibgeschützten Text mit einem Knopf zum Bearbeiten."""

    bearbeiten_angefordert = Signal(object, str)  # (EintragTyp, zeitraum)
    zurueck = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._typ = EintragTyp.TAG
        self._zeitraum = ""

        self.text_anzeige = QPlainTextEdit()
        self.text_anzeige.setReadOnly(True)

        self.bearbeiten_knopf = QPushButton("Bearbeiten")
        self.bearbeiten_knopf.setDefault(True)  # macht den Knopf per Enter bedienbar, sobald er fokussiert ist
        self.bearbeiten_knopf.clicked.connect(
            lambda: self.bearbeiten_angefordert.emit(self._typ, self._zeitraum)
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_anzeige, 1)
        layout.addWidget(self.bearbeiten_knopf)

        QWidget.setTabOrder(self.text_anzeige, self.bearbeiten_knopf)

        verlassen_kuerzel = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        verlassen_kuerzel.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        verlassen_kuerzel.activated.connect(self.zurueck.emit)

    def anzeigen(self, typ: EintragTyp, zeitraum: str, text: str) -> None:
        self._typ = typ
        self._zeitraum = zeitraum
        self.text_anzeige.setPlainText(text)
        name_widget(self.text_anzeige, _accessible_name(typ, zeitraum))
        cursor = self.text_anzeige.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_anzeige.setTextCursor(cursor)

    def fokus_text(self) -> None:
        self.text_anzeige.setFocus()
