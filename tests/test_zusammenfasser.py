"""Tests für ki/zusammenfasser.py (Abschnitt 9.1 des Konzepts)."""
from __future__ import annotations

import pytest

from kern.krypto import text_hmac
from kern.modelle import EintragTyp
from ki.ollama_client import OllamaFehler
from ki.zusammenfasser import (
    jahres_uebersicht_erzeugen,
    monats_uebersicht_erzeugen,
    tages_stichpunkte_erzeugen,
    veraltete_tage_finden,
)


class FakeClient:
    """Liefert der Reihe nach die in `antworten` hinterlegten Ergebnisse (oder wirft sie)."""

    def __init__(self, antworten: list) -> None:
        self._antworten = list(antworten)
        self.aufrufe = 0

    def json_anfrage(self, **_kwargs):
        self.aufrufe += 1
        antwort = self._antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort


def test_gueltige_antwort_wird_gespeichert(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Ein ereignisreicher Tag.")
    client = FakeClient([{"stichpunkte": ["Erstens", "Zweitens"]}])

    ergebnis = tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")

    assert ergebnis is True
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.stichpunkte == "- Erstens\n- Zweitens"
    assert eintrag.stichpunkte_quelle_hash == text_hmac("Ein ereignisreicher Tag.", schluessel)


def test_unbrauchbare_antwort_wird_einmal_wiederholt(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    client = FakeClient([{"falsches_feld": []}, {"stichpunkte": ["Erstens"]}])

    ergebnis = tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")

    assert ergebnis is True
    assert client.aufrufe == 2
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.stichpunkte == "- Erstens"


def test_dauerhaft_unbrauchbare_antwort_bleibt_ohne_stichpunkte(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    client = FakeClient([{"stichpunkte": "kein array"}, {"stichpunkte": []}])

    ergebnis = tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")

    assert ergebnis is False
    assert client.aufrufe == 2
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-09-22")
    assert eintrag.stichpunkte == ""


def test_zu_viele_stichpunkte_gelten_als_unbrauchbar(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    client = FakeClient(
        [{"stichpunkte": ["a", "b", "c", "d"]}, {"stichpunkte": ["a", "b", "c", "d"]}]
    )

    ergebnis = tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")
    assert ergebnis is False


def test_ollamafehler_wird_nicht_wiederholt_sondern_weitergereicht(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-22", "Text")
    client = FakeClient([OllamaFehler("nicht erreichbar")])

    with pytest.raises(OllamaFehler):
        tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")
    assert client.aufrufe == 1


def test_leerer_eintrag_wird_uebersprungen(speicher):
    schluessel = speicher.einrichten("passwort")
    client = FakeClient([])
    ergebnis = tages_stichpunkte_erzeugen(speicher, schluessel, "2026-09-22", client=client, modell="test")
    assert ergebnis is False
    assert client.aufrufe == 0


def test_veraltete_tage_findet_fehlende_stichpunkte(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text ohne Stichpunkte")
    assert veraltete_tage_finden(speicher, schluessel) == ["2026-09-20"]


def test_veraltete_tage_ignoriert_aktuelle_stichpunkte(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text")
    passender_hash = text_hmac("Text", schluessel)
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Punkt", passender_hash)
    assert veraltete_tage_finden(speicher, schluessel) == []


def test_veraltete_tage_erkennt_geaenderten_text(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Alter Text")
    alter_hash = text_hmac("Alter Text", schluessel)
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Punkt", alter_hash)
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", " Angehängt", anhaengen=True)

    assert veraltete_tage_finden(speicher, schluessel) == ["2026-09-20"]


def _mit_stichpunkten(speicher, schluessel, zeitraum: str, text: str, stichpunkte: str) -> None:
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, zeitraum, text)
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, zeitraum, stichpunkte, "hash")


def test_monatsuebersicht_wird_gespeichert(speicher):
    schluessel = speicher.einrichten("passwort")
    _mit_stichpunkten(speicher, schluessel, "2026-08-05", "Text 1", "- Punkt A")
    _mit_stichpunkten(speicher, schluessel, "2026-08-20", "Text 2", "- Punkt B")
    client = FakeClient(
        [{"text": "Ein ausführlicher Monatsrückblick.", "stichpunkte": ["a", "b", "c"]}]
    )

    ergebnis = monats_uebersicht_erzeugen(speicher, schluessel, "2026-08", client=client, modell="test")

    assert ergebnis is True
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08")
    assert eintrag.text == "Ein ausführlicher Monatsrückblick."
    assert eintrag.stichpunkte == "- a\n- b\n- c"
    assert eintrag.manuell_bearbeitet is False


def test_monat_ohne_tage_wird_uebersprungen(speicher):
    schluessel = speicher.einrichten("passwort")
    client = FakeClient([])
    ergebnis = monats_uebersicht_erzeugen(speicher, schluessel, "2026-08", client=client, modell="test")
    assert ergebnis is False
    assert client.aufrufe == 0


def test_monat_ignoriert_tage_ohne_stichpunkte(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-05", "Text ohne Stichpunkte")
    client = FakeClient([])
    ergebnis = monats_uebersicht_erzeugen(speicher, schluessel, "2026-08", client=client, modell="test")
    assert ergebnis is False
    assert client.aufrufe == 0


def test_monatsuebersicht_ueberschreiben_setzt_manuell_bearbeitet_zurueck(speicher):
    schluessel = speicher.einrichten("passwort")
    _mit_stichpunkten(speicher, schluessel, "2026-08-05", "Text", "- Punkt")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Von Hand geschrieben")
    speicher.manuell_bearbeitet_setzen(EintragTyp.MONAT, "2026-08", True)

    client = FakeClient([{"text": "Neue KI-Übersicht.", "stichpunkte": ["a", "b", "c"]}])
    ergebnis = monats_uebersicht_erzeugen(speicher, schluessel, "2026-08", client=client, modell="test")

    assert ergebnis is True
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08")
    assert eintrag.text == "Neue KI-Übersicht."
    assert eintrag.manuell_bearbeitet is False


def test_jahresuebersicht_wird_gespeichert(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2025-11", "Novemberrückblick")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2025-12", "Dezemberrückblick")
    client = FakeClient(
        [{"text": "Ein ausführlicher Jahresrückblick.", "stichpunkte": ["a", "b", "c", "d"]}]
    )

    ergebnis = jahres_uebersicht_erzeugen(speicher, schluessel, "2025", client=client, modell="test")

    assert ergebnis is True
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.JAHR, "2025")
    assert eintrag.text == "Ein ausführlicher Jahresrückblick."
    assert eintrag.stichpunkte == "- a\n- b\n- c\n- d"


def test_jahr_ohne_monatsuebersichten_wird_uebersprungen(speicher):
    schluessel = speicher.einrichten("passwort")
    client = FakeClient([])
    ergebnis = jahres_uebersicht_erzeugen(speicher, schluessel, "2025", client=client, modell="test")
    assert ergebnis is False
    assert client.aufrufe == 0


def test_uebersicht_mit_zu_kurzem_text_ist_unbrauchbar(speicher):
    schluessel = speicher.einrichten("passwort")
    _mit_stichpunkten(speicher, schluessel, "2026-08-05", "Text", "- Punkt")
    client = FakeClient(
        [{"text": "", "stichpunkte": ["a", "b", "c"]}, {"text": "", "stichpunkte": ["a", "b", "c"]}]
    )
    ergebnis = monats_uebersicht_erzeugen(speicher, schluessel, "2026-08", client=client, modell="test")
    assert ergebnis is False
    assert client.aufrufe == 2
