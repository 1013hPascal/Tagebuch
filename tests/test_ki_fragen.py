"""Tests für ki/fragen.py (Erweiterung „Suche/Frage“ zu Abschnitt 7.6 des Konzepts)."""
from __future__ import annotations

import pytest

from kern.modelle import EintragTyp
from ki.fragen import KEIN_KONTEXT, frage_beantworten
from ki.ollama_client import OllamaFehler


class FakeClient:
    def __init__(self, antwort=None, *, fehler: Exception | None = None) -> None:
        self._antwort = antwort
        self._fehler = fehler
        self.aufrufe: list[dict] = []

    def json_anfrage(self, **kwargs):
        self.aufrufe.append(kwargs)
        if self._fehler is not None:
            raise self._fehler
        return self._antwort


def test_ohne_eintraege_kommt_hinweis_ohne_ki_aufruf(speicher):
    schluessel = speicher.einrichten("passwort")
    client = FakeClient({"antwort": "sollte nicht aufgerufen werden"})

    ergebnis = frage_beantworten(speicher, schluessel, "Wann war ich im Urlaub?", client=client, modell="test")

    assert ergebnis == KEIN_KONTEXT
    assert client.aufrufe == []


def test_kontext_enthaelt_uebersichten_und_tages_stichpunkte(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.JAHR, "2025", "Jahresrückblick 2025.")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Rückblick August.")
    # Tag im August gehört zu einer vorhandenen Monatsübersicht -> nicht extra im Kontext.
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-15", "Text im August")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-08-15", "- August-Punkt", "hash")
    # Tag im September hat noch keine Monatsübersicht -> Stichpunkte gehören in den Kontext.
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text im September")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- September-Punkt", "hash")

    client = FakeClient({"antwort": "Die Antwort."})
    ergebnis = frage_beantworten(speicher, schluessel, "Wie war das Jahr?", client=client, modell="test")

    assert ergebnis == "Die Antwort."
    prompt = client.aufrufe[0]["prompt"]
    assert "Jahresrückblick 2025." in prompt
    assert "Rückblick August." in prompt
    assert "September-Punkt" in prompt
    assert "August-Punkt" not in prompt  # bereits in der Monatsübersicht enthalten


def test_ungueltige_antwort_loest_fehler_aus(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Punkt", "hash")
    client = FakeClient({"falsches_feld": "x"})

    with pytest.raises(ValueError):
        frage_beantworten(speicher, schluessel, "Frage?", client=client, modell="test")


def test_ollama_fehler_wird_weitergereicht(speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Punkt", "hash")
    client = FakeClient(fehler=OllamaFehler("Ollama ist nicht erreichbar."))

    with pytest.raises(OllamaFehler):
        frage_beantworten(schluessel=schluessel, speicher=speicher, frage="Frage?", client=client, modell="test")
