"""Hintergrund-Task auf Basis von QThread (Muster aus dem Chatbot-Projekt übernommen).

Damit friert die Oberfläche während Spracherkennung oder Ollama-Anfragen nie
ein. Fehler im Thread werden immer über ein Signal gemeldet, nie stillschweigend
verschluckt.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


class Cancelled(Exception):
    """Der Nutzer hat den Vorgang abgebrochen."""


class AufgabenFehler(Exception):
    """Ein erwarteter, verständlicher Fehler (z. B. Ollama nicht erreichbar)."""


class Task(QThread):
    """Führt `fn(self)` in einem eigenen Thread aus.

    `fn` bekommt den Task selbst übergeben, um `cancel_event` zu prüfen und
    über `progress` Statusmeldungen an die Oberfläche zu senden.
    """

    progress = Signal(float, str)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, fn: Callable[["Task"], object], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            outcome = self._fn(self)
        except Cancelled:
            self.cancelled.emit()
        except AufgabenFehler as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # nie den Thread still sterben lassen
            log.exception("Unerwarteter Fehler im Hintergrund-Task")
            self.error.emit(f"Unerwarteter Fehler: {exc}")
        else:
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.result.emit(outcome)
