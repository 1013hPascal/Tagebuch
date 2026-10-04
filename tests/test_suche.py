"""Tests für Speicher.suchen() (Abschnitt 7.6 des Konzepts)."""
from __future__ import annotations

from kern.modelle import EintragTyp


def test_suche_findet_treffer_im_text(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Ein Tag im Urlaub in Italien.")
    treffer = speicher.suchen(schluessel, "Urlaub")
    assert len(treffer) == 1
    assert treffer[0].eintrag.zeitraum == "2026-09-20"


def test_suche_ohne_beachtung_von_gross_und_kleinschreibung(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Ein Tag im URLAUB.")
    treffer = speicher.suchen(schluessel, "urlaub")
    assert len(treffer) == 1


def test_suche_findet_treffer_in_stichpunkten(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text ohne das Wort.")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Ausflug ans Meer", "hash")
    treffer = speicher.suchen(schluessel, "Meer")
    assert len(treffer) == 1
    assert treffer[0].ausschnitt


def test_suche_ueber_tage_monate_und_jahre(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Urlaub am Tag")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Urlaub im Monat")
    speicher.eintrag_speichern(schluessel, EintragTyp.JAHR, "2025", "Urlaub im Jahr")
    treffer = speicher.suchen(schluessel, "Urlaub")
    assert len(treffer) == 3


def test_suche_neueste_zuerst(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Alter Urlaub")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Neuer Urlaub")
    treffer = speicher.suchen(schluessel, "Urlaub")
    assert [t.eintrag.zeitraum for t in treffer] == ["2026-09-20", "2020-01-01"]


def test_suche_ohne_treffer(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Ein ganz normaler Tag.")
    assert speicher.suchen(schluessel, "Nichtvorhanden") == []


def test_ausschnitt_enthaelt_kontext_um_die_fundstelle(speicher):
    schluessel = speicher.einrichten("passwort")
    text = "x" * 100 + "GEFUNDEN" + "y" * 100
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", text)
    treffer = speicher.suchen(schluessel, "GEFUNDEN")
    assert "GEFUNDEN" in treffer[0].ausschnitt
    assert treffer[0].ausschnitt.startswith("… ")
    assert treffer[0].ausschnitt.endswith(" …")
    assert len(treffer[0].ausschnitt) < len(text)
