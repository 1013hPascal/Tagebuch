"""Tests für kern/zeitplan.py (Abschnitt 9.2, 9.3 und 10 des Konzepts)."""
from __future__ import annotations

from datetime import date

from kern.modelle import EintragTyp
from kern.zeitplan import faellige_jahre, faellige_monate

HEUTE = date(2026, 9, 22)


def test_kein_tag_kein_faelliger_monat(speicher):
    schluessel = speicher.einrichten("passwort")
    assert faellige_monate(speicher, schluessel, HEUTE) == []


def test_vergangener_monat_mit_tag_ist_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-15", "Text")
    assert faellige_monate(speicher, schluessel, HEUTE) == ["2026-08"]


def test_aktueller_monat_ist_nicht_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-01", "Text")
    assert faellige_monate(speicher, schluessel, HEUTE) == []


def test_monat_mit_vorhandener_uebersicht_ist_nicht_mehr_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-15", "Text")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Schon vorhanden")
    assert faellige_monate(speicher, schluessel, HEUTE) == []


def test_mehrere_faellige_monate_aeltester_zuerst(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-06-01", "Text")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-01", "Text")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-07-01", "Text")
    assert faellige_monate(speicher, schluessel, HEUTE) == ["2026-06", "2026-07", "2026-08"]


def test_vergangenes_jahr_mit_monat_ist_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2025-12", "Text")
    assert faellige_jahre(speicher, schluessel, HEUTE) == ["2025"]


def test_aktuelles_jahr_ist_nicht_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-01", "Text")
    assert faellige_jahre(speicher, schluessel, HEUTE) == []


def test_jahr_mit_vorhandener_uebersicht_ist_nicht_mehr_faellig(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2025-12", "Text")
    speicher.eintrag_speichern(schluessel, EintragTyp.JAHR, "2025", "Schon vorhanden")
    assert faellige_jahre(speicher, schluessel, HEUTE) == []
