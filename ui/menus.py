"""Barrierefreie Menüs (Muster aus dem Chatbot-Projekt übernommen).

Ein normales QMenu meldet dem Screenreader beim Öffnen oft nur den
Programmnamen, und der erste Eintrag wird nicht zuverlässig vorgelesen.
AccessibleMenu behebt beides: eigener Accessible Name plus eine kurz
verzögerte, erneute Fokus-Ansage des ersten Eintrags.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QMenu, QWidget


class AccessibleMenu(QMenu):
    def __init__(self, titel: str, parent: QWidget | None = None) -> None:
        super().__init__(titel, parent)
        # Der Titel kann ein Alt-Kürzel-Zeichen ("&") enthalten, das im Accessible Name nicht auftauchen soll.
        self.setAccessibleName(titel.replace("&", ""))
        self.aboutToShow.connect(self._ersten_eintrag_ansagen)

    def _ersten_eintrag_ansagen(self) -> None:
        aktionen = [a for a in self.actions() if not a.isSeparator()]
        if not aktionen:
            return
        self.setActiveAction(aktionen[0])
        QTimer.singleShot(200, self._fokus_erneut_melden)

    def _fokus_erneut_melden(self) -> None:
        QAccessible.updateAccessibility(QAccessibleEvent(self, QAccessible.Event.Focus))
