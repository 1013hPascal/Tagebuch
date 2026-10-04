"""Datenmodelle für Tagebucheinträge (Abschnitt 6 des Konzepts)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EintragTyp(str, Enum):
    TAG = "tag"
    MONAT = "monat"
    JAHR = "jahr"


@dataclass
class Eintrag:
    id: int | None
    typ: EintragTyp
    zeitraum: str  # "JJJJ-MM-TT", "JJJJ-MM" oder "JJJJ"
    text: str
    stichpunkte: str
    stichpunkte_quelle_hash: str
    manuell_bearbeitet: bool
    erstellt_am: datetime
    geaendert_am: datetime


@dataclass
class Suchtreffer:
    """Ein Suchergebnis (Abschnitt 7.6): der Eintrag plus ein Textausschnitt um die Fundstelle."""

    eintrag: Eintrag
    ausschnitt: str
