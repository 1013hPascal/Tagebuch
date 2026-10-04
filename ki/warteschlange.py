"""Warteschlange für Hintergrund-Aufgaben der KI-Zusammenfassungen (Abschnitt 9 des Konzepts).

Reine Warteschlangen-Logik ohne Qt-Abhängigkeit, damit sie sich leicht testen
lässt. Die Ausführung im Hintergrund-Thread übernimmt ui/ki_worker.py.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

from kern.modelle import EintragTyp


@dataclass
class Auftrag:
    typ: EintragTyp
    zeitraum: str
    beschreibung: str  # für die Statuszeile, z. B. "Erstelle Stichpunkte für ... "
    ausfuehren: Callable[[], None]


class Warteschlange:
    """FIFO-Warteschlange. `naechster()` entfernt und liefert den nächsten Auftrag."""

    def __init__(self) -> None:
        self._auftraege: deque[Auftrag] = deque()

    def hinzufuegen(self, auftrag: Auftrag) -> None:
        self._auftraege.append(auftrag)

    def ist_leer(self) -> bool:
        return not self._auftraege

    def naechster(self) -> Auftrag:
        return self._auftraege.popleft()

    def __len__(self) -> int:
        return len(self._auftraege)
