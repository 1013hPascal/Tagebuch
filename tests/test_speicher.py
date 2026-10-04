"""Tests für kern/speicher.py."""
from __future__ import annotations

import pytest

from kern.krypto import FalschesPasswort
from kern.modelle import EintragTyp
from kern.speicher import BereitsEingerichtet, NichtEingerichtet


def test_neue_datenbank_ist_nicht_eingerichtet(speicher):
    assert speicher.ist_eingerichtet() is False


def test_einrichten_und_anmelden(speicher):
    schluessel = speicher.einrichten("mein-passwort")
    assert speicher.ist_eingerichtet() is True
    assert speicher.anmelden("mein-passwort") == schluessel


def test_anmelden_mit_falschem_passwort(speicher):
    speicher.einrichten("richtig")
    with pytest.raises(FalschesPasswort):
        speicher.anmelden("falsch")


def test_anmelden_ohne_account(speicher):
    with pytest.raises(NichtEingerichtet):
        speicher.anmelden("irgendwas")


def test_doppeltes_einrichten_schlaegt_fehl(speicher):
    speicher.einrichten("passwort")
    with pytest.raises(BereitsEingerichtet):
        speicher.einrichten("anderes-passwort")


def test_eintrag_speichern_und_laden(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Heute war ein guter Tag.")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag is not None
    assert eintrag.text == "Heute war ein guter Tag."
    assert eintrag.manuell_bearbeitet is False


def test_eintrag_anhaengen(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Erster Satz.")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Zweiter Satz.", anhaengen=True)
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.text == "Erster Satz.\n\nZweiter Satz."


def test_eintrag_ueberschreiben_ohne_anhaengen(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Alt.")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Neu.", anhaengen=False)
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.text == "Neu."


def test_eintrag_laden_nicht_vorhanden(speicher):
    schluessel = speicher.einrichten("passwort")
    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2020-01-01") is None


def test_eintraege_liste_neueste_zuerst(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Alt")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Neu")
    liste = speicher.eintraege_liste(schluessel, EintragTyp.TAG)
    assert [e.zeitraum for e in liste] == ["2026-09-22", "2026-09-20"]


def test_eintrag_loeschen(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    speicher.eintrag_loeschen(EintragTyp.TAG, "2026-09-22")
    assert speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22") is None


def test_passwort_aendern_entschluesselt_weiterhin(speicher):
    alt = speicher.einrichten("altes-passwort")
    speicher.eintrag_speichern(alt, EintragTyp.TAG, "2026-09-22", "Geheimer Text")
    neu = speicher.passwort_aendern(alt, "neues-passwort")
    assert speicher.anmelden("neues-passwort") == neu
    with pytest.raises(FalschesPasswort):
        speicher.anmelden("altes-passwort")
    eintrag = speicher.eintrag_laden(neu, EintragTyp.TAG, "2026-09-22")
    assert eintrag.text == "Geheimer Text"


def test_account_loeschen_entfernt_datei(speicher):
    speicher.einrichten("passwort")
    pfad = speicher.pfad
    assert pfad.exists()
    speicher.account_loeschen()
    assert not pfad.exists()


def test_stichpunkte_speichern_und_laden(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "- Punkt eins", "hash123")
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.stichpunkte == "- Punkt eins"
    assert eintrag.stichpunkte_quelle_hash == "hash123"


def test_manuell_bearbeitet_setzen(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Text")
    assert speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08").manuell_bearbeitet is False

    speicher.manuell_bearbeitet_setzen(EintragTyp.MONAT, "2026-08", True)
    assert speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08").manuell_bearbeitet is True

    speicher.manuell_bearbeitet_setzen(EintragTyp.MONAT, "2026-08", False)
    assert speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08").manuell_bearbeitet is False


def test_last_run_date(speicher):
    assert speicher.last_run_date_holen() is None
    speicher.last_run_date_setzen("2026-09-22")
    assert speicher.last_run_date_holen() == "2026-09-22"
    speicher.last_run_date_setzen("2026-09-23")
    assert speicher.last_run_date_holen() == "2026-09-23"
