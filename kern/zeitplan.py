"""Bestimmt, welche Monats- und Jahresübersichten fällig sind (Abschnitt 9.2, 9.3 und 10
des Konzepts). Das heutige Datum wird als Parameter übergeben, damit sich Monats- und
Jahreswechsel testen lassen.

Ein Monat/Jahr gilt als fällig, wenn er abgeschlossen ist (vor dem aktuellen Monat/Jahr
liegt), mindestens einen zugehörigen Eintrag hat, und noch keine Übersicht existiert. Ist
einmal eine Übersicht vorhanden, wird sie nicht automatisch neu erzeugt (Annahme A7) -
das übernimmt nur „Zusammenfassung neu erstellen“.
"""
from __future__ import annotations

from datetime import date

from .modelle import EintragTyp
from .speicher import Speicher


def faellige_monate(speicher: Speicher, schluessel: bytes, heute: date) -> list[str]:
    """Monate mit mindestens einem Tageseintrag, vor dem aktuellen Monat, ohne Übersicht.
    Ältester zuerst."""
    aktueller_monat = f"{heute.year:04d}-{heute.month:02d}"
    vorhandene_monate = {e.zeitraum for e in speicher.eintraege_liste(schluessel, EintragTyp.MONAT)}
    monate_mit_tagen = sorted({e.zeitraum[:7] for e in speicher.eintraege_liste(schluessel, EintragTyp.TAG)})
    return [
        monat for monat in monate_mit_tagen if monat < aktueller_monat and monat not in vorhandene_monate
    ]


def faellige_jahre(speicher: Speicher, schluessel: bytes, heute: date) -> list[str]:
    """Jahre mit mindestens einer Monatsübersicht, vor dem aktuellen Jahr, ohne Übersicht.
    Ältester zuerst."""
    aktuelles_jahr = f"{heute.year:04d}"
    vorhandene_jahre = {e.zeitraum for e in speicher.eintraege_liste(schluessel, EintragTyp.JAHR)}
    jahre_mit_monaten = sorted({e.zeitraum[:4] for e in speicher.eintraege_liste(schluessel, EintragTyp.MONAT)})
    return [
        jahr for jahr in jahre_mit_monaten if jahr < aktuelles_jahr and jahr not in vorhandene_jahre
    ]
