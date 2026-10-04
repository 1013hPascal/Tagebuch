"""Datumsformate und Prüfung (Abschnitt 8 des Konzepts)."""
from __future__ import annotations

import re
from datetime import date

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATSNAMEN = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

_TAG_MUSTER = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$")
_MONAT_MUSTER = re.compile(r"^\s*(\d{1,2})\.(\d{4})\s*$")
_JAHR_MUSTER = re.compile(r"^\s*(\d{4})\s*$")


class DatumFehler(Exception):
    """Das eingegebene Datum ist ungültig. `nachricht` ist für die Anzeige gedacht."""

    def __init__(self, nachricht: str) -> None:
        super().__init__(nachricht)
        self.nachricht = nachricht


def tag_parsen(text: str, heute: date) -> str:
    """Wandelt 'TT.MM.JJJJ' in 'JJJJ-MM-TT' um. Prüft Existenz und dass es nicht in der Zukunft liegt."""
    passend = _TAG_MUSTER.match(text)
    if not passend:
        raise DatumFehler("Bitte das Datum im Format TT.MM.JJJJ eingeben.")
    tag, monat, jahr = (int(teil) for teil in passend.groups())
    try:
        datum = date(jahr, monat, tag)
    except ValueError:
        raise DatumFehler(
            f"Das Datum {tag:02d}.{monat:02d}.{jahr:04d} gibt es nicht. "
            "Bitte im Format TT.MM.JJJJ eingeben."
        ) from None
    if datum > heute:
        raise DatumFehler("Das Datum darf nicht in der Zukunft liegen.")
    return datum.isoformat()


def monat_parsen(text: str, heute: date) -> str:
    """Wandelt 'MM.JJJJ' in 'JJJJ-MM' um."""
    passend = _MONAT_MUSTER.match(text)
    if not passend:
        raise DatumFehler("Bitte den Monat im Format MM.JJJJ eingeben.")
    monat, jahr = (int(teil) for teil in passend.groups())
    if not 1 <= monat <= 12:
        raise DatumFehler(
            f"Den Monat {monat:02d}.{jahr:04d} gibt es nicht. Bitte im Format MM.JJJJ eingeben."
        )
    if (jahr, monat) > (heute.year, heute.month):
        raise DatumFehler("Der Monat darf nicht in der Zukunft liegen.")
    return f"{jahr:04d}-{monat:02d}"


def jahr_parsen(text: str, heute: date) -> str:
    """Prüft 'JJJJ'."""
    passend = _JAHR_MUSTER.match(text)
    if not passend:
        raise DatumFehler("Bitte das Jahr im Format JJJJ eingeben.")
    jahr = int(passend.group(1))
    if jahr > heute.year:
        raise DatumFehler("Das Jahr darf nicht in der Zukunft liegen.")
    return f"{jahr:04d}"


def tag_anzeigen(zeitraum: str) -> str:
    """'JJJJ-MM-TT' -> 'Dienstag, 22.09.2026'"""
    jahr, monat, tag = (int(teil) for teil in zeitraum.split("-"))
    wochentag = WOCHENTAGE[date(jahr, monat, tag).weekday()]
    return f"{wochentag}, {tag:02d}.{monat:02d}.{jahr:04d}"


def monat_anzeigen(zeitraum: str) -> str:
    """'JJJJ-MM' -> 'September 2026'"""
    jahr, monat = (int(teil) for teil in zeitraum.split("-"))
    return f"{MONATSNAMEN[monat - 1]} {jahr:04d}"


def jahr_anzeigen(zeitraum: str) -> str:
    """'JJJJ' -> 'JJJJ' (bereits die Anzeigeform)."""
    return zeitraum
