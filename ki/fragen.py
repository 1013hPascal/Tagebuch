"""Beantwortet Fragen zur Vergangenheit (Erweiterung „Suche/Frage“ zu Abschnitt 7.6).

Als Kontext dienen dieselben Zusammenfassungen, die für die Rückschau ohnehin erzeugt
werden (Jahres-/Monatsübersichten, Tages-Stichpunkte) - kein erneutes Einlesen der vollen
Rohtexte nötig, und der Kontext bleibt auch nach Jahren kompakt genug fürs Kontextfenster,
weil ältere Tage bereits in Monats-/Jahresübersichten verdichtet sind.
"""
from __future__ import annotations

from kern import datum
from kern.modelle import EintragTyp
from kern.speicher import Speicher

from . import prompts
from .ollama_client import OllamaClient

KEIN_KONTEXT = "Dazu gibt es noch keine Einträge oder Zusammenfassungen."


def frage_beantworten(
    speicher: Speicher,
    schluessel: bytes,
    frage: str,
    *,
    client: OllamaClient,
    modell: str,
    num_ctx: int | None = None,
) -> str:
    """Fragt das Modell anhand der vorhandenen Zusammenfassungen. Löst OllamaFehler weiter
    nach oben, wenn Ollama nicht erreichbar ist (Abschnitt 9.5 gilt sinngemäß)."""
    kontext = _kontext_aufbauen(speicher, schluessel)
    if not kontext.strip():
        return KEIN_KONTEXT

    daten = client.json_anfrage(
        modell=modell,
        system=prompts.FRAGE_SYSTEM,
        prompt=prompts.frage_prompt(frage, kontext),
        schema=prompts.FRAGE_SCHEMA,
        num_ctx=num_ctx,
    )
    antwort = daten.get("antwort") if isinstance(daten, dict) else None
    if not isinstance(antwort, str) or not antwort.strip():
        raise ValueError("Antwort war kein gültiges JSON.")
    return antwort.strip()


def _kontext_aufbauen(speicher: Speicher, schluessel: bytes) -> str:
    """Jahres- und Monatsübersichten (ausführlich), dazu Tages-Stichpunkte aller Tage, die
    noch zu keiner Monatsübersicht gehören (z. B. der laufende Monat). Älteste zuerst."""
    jahre = sorted(speicher.eintraege_liste(schluessel, EintragTyp.JAHR), key=lambda e: e.zeitraum)
    monate = sorted(speicher.eintraege_liste(schluessel, EintragTyp.MONAT), key=lambda e: e.zeitraum)
    monate_mit_uebersicht = {m.zeitraum for m in monate if m.text.strip()}
    tage = sorted(speicher.eintraege_liste(schluessel, EintragTyp.TAG), key=lambda e: e.zeitraum)

    abschnitte: list[str] = []
    for jahr in jahre:
        if jahr.text.strip():
            abschnitte.append(f"Jahresübersicht {datum.jahr_anzeigen(jahr.zeitraum)}:\n{jahr.text.strip()}")
    for monat in monate:
        if monat.text.strip():
            abschnitte.append(f"Monatsübersicht {datum.monat_anzeigen(monat.zeitraum)}:\n{monat.text.strip()}")
    for tag in tage:
        if tag.zeitraum[:7] in monate_mit_uebersicht:
            continue
        if tag.stichpunkte.strip():
            abschnitte.append(f"{datum.tag_anzeigen(tag.zeitraum)}:\n{tag.stichpunkte.strip()}")
        elif tag.text.strip():
            abschnitte.append(f"{datum.tag_anzeigen(tag.zeitraum)}:\n{tag.text.strip()}")

    return "\n\n".join(abschnitte)
