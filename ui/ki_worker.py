"""Verarbeitet die KI-Warteschlange sequenziell im Hintergrund (Abschnitt 9 des Konzepts).

Ein Auftrag nach dem anderen läuft in einem Task (QThread), damit die
Oberfläche bedienbar bleibt. Ist Ollama nicht erreichbar, wird das einmalig
gemeldet und die Warteschlange für diese Sitzung nicht weiter automatisch
abgearbeitet (Abschnitt 9.5) - ein neuer Auftrag (z. B. durch erneutes
Speichern) versucht es beim nächsten Aufruf erneut.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from ki.ollama_client import WARTE_TIMEOUT_MS, OllamaFehler
from ki.warteschlange import Auftrag, Warteschlange

from .workers import Task

log = logging.getLogger(__name__)

_ERGEBNIS_ERLEDIGT = "erledigt"
_ERGEBNIS_NICHT_ERREICHBAR = "nicht_erreichbar"


class KiWarteschlangenVerarbeiter(QObject):
    status_geaendert = Signal(str)
    auftrag_gestartet = Signal(object, str)  # (EintragTyp, zeitraum)
    auftrag_fertig = Signal(object, str)  # (EintragTyp, zeitraum)
    nicht_erreichbar = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._warteschlange = Warteschlange()
        self._laufender_auftrag: Auftrag | None = None
        self._task: Task | None = None
        self._nicht_erreichbar_gemeldet = False

    def hinzufuegen(self, auftrag: Auftrag) -> None:
        self._warteschlange.hinzufuegen(auftrag)
        self._weiter()

    def laeuft_gerade(self) -> bool:
        return self._task is not None

    def abbrechen_und_warten(self, timeout_ms: int = WARTE_TIMEOUT_MS) -> None:
        """Für das Beenden des Programms: wartet, bis ein laufender Task wirklich fertig ist,
        statt ihn mitten in der Ausführung zu zerstören (das würde den Prozess abstürzen lassen).

        Der Timeout ist bewusst so groß wie die Ollama-Anfrage selbst (siehe
        ki/ollama_client.WARTE_TIMEOUT_MS): Ein frisch gestartetes großes Modell (z. B.
        gemma4:12b) muss erst von der Platte geladen werden, das dauert oft deutlich länger als
        ein paar Sekunden. Ein zu kurzer Timeout hier würde eine laufende Zusammenfassung
        beim Schließen des Programms killen, bevor sie fertig ist."""
        if self._task is not None:
            self._task.cancel()
            self._task.wait(timeout_ms)

    def _weiter(self) -> None:
        if self._task is not None or self._warteschlange.ist_leer():
            return
        auftrag = self._laufender_auftrag = self._warteschlange.naechster()
        self.status_geaendert.emit(auftrag.beschreibung)
        self.auftrag_gestartet.emit(auftrag.typ, auftrag.zeitraum)

        def arbeit(_task: Task) -> str:
            try:
                auftrag.ausfuehren()
                return _ERGEBNIS_ERLEDIGT
            except OllamaFehler:
                return _ERGEBNIS_NICHT_ERREICHBAR

        task = Task(arbeit, self)
        task.result.connect(self._auftrag_erledigt)
        task.error.connect(self._unerwarteter_fehler)
        task.cancelled.connect(self._auftrag_abgebrochen)
        task.finished.connect(task.deleteLater)
        self._task = task
        task.start()

    def _auftrag_erledigt(self, ergebnis: str) -> None:
        auftrag = self._laufender_auftrag
        self._task = None
        self._laufender_auftrag = None

        if ergebnis == _ERGEBNIS_NICHT_ERREICHBAR:
            if not self._nicht_erreichbar_gemeldet:
                self._nicht_erreichbar_gemeldet = True
                self.nicht_erreichbar.emit()
            return  # Warteschlange für diese Sitzung anhalten (Abschnitt 9.5)

        self._nicht_erreichbar_gemeldet = False
        if auftrag is not None:
            self.auftrag_fertig.emit(auftrag.typ, auftrag.zeitraum)
        self._weiter()

    def _unerwarteter_fehler(self, fehlertext: str) -> None:
        log.error("Unerwarteter Fehler in der KI-Warteschlange: %s", fehlertext)
        self._task = None
        self._laufender_auftrag = None
        self._weiter()

    def _auftrag_abgebrochen(self) -> None:
        # Passiert nur beim Beenden des Programms (abbrechen_und_warten). Absichtlich
        # kein _weiter() hier: es soll keine neue Arbeit mehr angestoßen werden.
        self._task = None
        self._laufender_auftrag = None
