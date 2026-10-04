"""Ansagen für den Screenreader (Abschnitt 11 des Konzepts, Muster aus dem Chatbot-Projekt).

Nutzt echte Qt-Accessibility-Events (QAccessibleAnnouncementEvent, ab Qt 6.8)
statt Statuszeile allein oder Timer-Polling. So liest der Screenreader den
Text unabhängig vom aktuellen Fokus vor, und Hintergrundmeldungen verschieben
den Fokus nicht.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject
from PySide6.QtGui import QAccessible, QAccessibleEvent

log = logging.getLogger(__name__)

try:
    from PySide6.QtGui import QAccessibleAnnouncementEvent
except ImportError:  # ältere Qt-Version als 6.8
    QAccessibleAnnouncementEvent = None


class Announcer:
    """Sendet Ansagen an den Screenreader. `target` ist meist das Hauptfenster."""

    def __init__(self) -> None:
        self.target: QObject | None = None
        self.last_text = ""
        self.history: list[tuple[str, bool]] = []

    def announce(self, text: str, dringend: bool = False) -> None:
        self.last_text = text
        self.history.append((text, dringend))
        log.info("Ansage: %s%s", text, " (dringend)" if dringend else "")
        target = self.target
        if target is None:
            return
        if QAccessibleAnnouncementEvent is not None:
            event = QAccessibleAnnouncementEvent(target, text)
            event.setPoliteness(
                QAccessible.AnnouncementPoliteness.Assertive
                if dringend
                else QAccessible.AnnouncementPoliteness.Polite
            )
        else:
            event = QAccessibleEvent(target, QAccessible.Event.NameChanged)
        QAccessible.updateAccessibility(event)


announcer = Announcer()


def announce(text: str, dringend: bool = False) -> None:
    announcer.announce(text, dringend)
