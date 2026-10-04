"""Erzeugt KI-Zusammenfassungen (Abschnitt 9 des Konzepts).

Ist die Modellausgabe unbrauchbar (kein gültiges JSON oder falsche Form), wird
einmal wiederholt; bleibt sie unbrauchbar, bleibt der Eintrag ohne
Zusammenfassung und wird beim nächsten Start erneut versucht. Ist Ollama
nicht erreichbar, wird das nicht wiederholt, sondern an den Aufrufer
gemeldet (Abschnitt 9.5) - dafür ist die Warteschlange zuständig.
"""
from __future__ import annotations

import logging

from kern import datum
from kern.krypto import text_hmac
from kern.modelle import Eintrag, EintragTyp
from kern.speicher import Speicher

from . import prompts
from .ollama_client import OllamaClient, OllamaFehler

log = logging.getLogger(__name__)

_MAX_VERSUCHE = 2  # 1 Versuch + 1 Wiederholung bei unbrauchbarer Ausgabe


def tages_stichpunkte_erzeugen(
    speicher: Speicher, schluessel: bytes, zeitraum: str, *, client: OllamaClient, modell: str
) -> bool:
    """Erzeugt und speichert die Stichpunkte eines Tages. True bei Erfolg, sonst False.

    Löst OllamaFehler weiter nach oben, wenn Ollama nicht erreichbar ist.
    """
    eintrag = speicher.eintrag_laden(schluessel, EintragTyp.TAG, zeitraum)
    if eintrag is None or not eintrag.text.strip():
        return False

    for versuch in range(1, _MAX_VERSUCHE + 1):
        try:
            daten = client.json_anfrage(
                modell=modell,
                system=prompts.TAGES_STICHPUNKTE_SYSTEM,
                prompt=prompts.tages_stichpunkte_prompt(eintrag.text),
                schema=prompts.TAGES_STICHPUNKTE_SCHEMA,
            )
        except OllamaFehler:
            raise
        except Exception:
            log.warning("Unbrauchbare Ausgabe bei Tages-Stichpunkten für %s (Versuch %s)", zeitraum, versuch)
            continue

        stichpunkte = _stichpunkte_pruefen(daten)
        if stichpunkte is None:
            log.warning("Unbrauchbare Ausgabe bei Tages-Stichpunkten für %s (Versuch %s)", zeitraum, versuch)
            continue

        text = "\n".join(f"- {punkt}" for punkt in stichpunkte)
        quelle_hash = text_hmac(eintrag.text, schluessel)
        speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, zeitraum, text, quelle_hash)
        return True

    log.warning("Tages-Stichpunkte für %s blieben nach %s Versuchen unbrauchbar.", zeitraum, _MAX_VERSUCHE)
    return False


def monats_uebersicht_erzeugen(
    speicher: Speicher,
    schluessel: bytes,
    zeitraum: str,
    *,
    client: OllamaClient,
    modell: str,
    num_ctx: int | None = None,
) -> bool:
    """Erzeugt und speichert die Monatsübersicht (Abschnitt 9.2). True bei Erfolg.

    Überschreibt einen vorhandenen Eintrag bedingungslos - ob das automatisch geschehen
    darf (z. B. nicht bei manuell bearbeiteten Übersichten), entscheidet der Aufrufer
    (kern/zeitplan.py bzw. die Bestätigung bei „Zusammenfassung neu erstellen“).
    """
    jahr, monat = (int(teil) for teil in zeitraum.split("-"))
    tage = sorted(_tage_des_monats(speicher, schluessel, jahr, monat), key=lambda e: e.zeitraum)
    eingabe = [(datum.tag_anzeigen(tag.zeitraum), tag.stichpunkte) for tag in tage if tag.stichpunkte]
    if not eingabe:
        return False

    erfolg = _uebersicht_erzeugen(
        speicher,
        schluessel,
        EintragTyp.MONAT,
        zeitraum,
        client=client,
        modell=modell,
        system=prompts.MONATS_UEBERSICHT_SYSTEM,
        prompt=prompts.monats_uebersicht_prompt(eingabe),
        num_ctx=num_ctx,
    )
    return erfolg


def jahres_uebersicht_erzeugen(
    speicher: Speicher,
    schluessel: bytes,
    zeitraum: str,
    *,
    client: OllamaClient,
    modell: str,
    num_ctx: int | None = None,
) -> bool:
    """Erzeugt und speichert die Jahresübersicht (Abschnitt 9.3). True bei Erfolg."""
    jahr = int(zeitraum)
    monate = sorted(_monate_des_jahres(speicher, schluessel, jahr), key=lambda e: e.zeitraum)
    eingabe = [(datum.monat_anzeigen(monat.zeitraum), monat.text) for monat in monate if monat.text.strip()]
    if not eingabe:
        return False

    return _uebersicht_erzeugen(
        speicher,
        schluessel,
        EintragTyp.JAHR,
        zeitraum,
        client=client,
        modell=modell,
        system=prompts.JAHRES_UEBERSICHT_SYSTEM,
        prompt=prompts.jahres_uebersicht_prompt(eingabe),
        num_ctx=num_ctx,
    )


def _uebersicht_erzeugen(
    speicher: Speicher,
    schluessel: bytes,
    typ: EintragTyp,
    zeitraum: str,
    *,
    client: OllamaClient,
    modell: str,
    system: str,
    prompt: str,
    num_ctx: int | None = None,
) -> bool:
    for versuch in range(1, _MAX_VERSUCHE + 1):
        try:
            daten = client.json_anfrage(
                modell=modell, system=system, prompt=prompt, schema=prompts.UEBERSICHT_SCHEMA, num_ctx=num_ctx
            )
        except OllamaFehler:
            raise
        except Exception:
            log.warning("Unbrauchbare Ausgabe bei %s-Übersicht für %s (Versuch %s)", typ.value, zeitraum, versuch)
            continue

        geprueft = _text_und_stichpunkte_pruefen(daten)
        if geprueft is None:
            log.warning("Unbrauchbare Ausgabe bei %s-Übersicht für %s (Versuch %s)", typ.value, zeitraum, versuch)
            continue

        text, stichpunkte = geprueft
        speicher.eintrag_speichern(schluessel, typ, zeitraum, text, anhaengen=False)
        stichpunkte_text = "\n".join(f"- {punkt}" for punkt in stichpunkte)
        # Der Quelle-Hash wird für Monat/Jahr nicht zur Veraltungsprüfung genutzt (Annahme A7);
        # das Feld bleibt hier ungenutzt, ist aber Teil des gemeinsamen Datenmodells (Abschnitt 6).
        speicher.stichpunkte_speichern(schluessel, typ, zeitraum, stichpunkte_text, "")
        speicher.manuell_bearbeitet_setzen(typ, zeitraum, False)
        return True

    log.warning("%s-Übersicht für %s blieb nach %s Versuchen unbrauchbar.", typ.value, zeitraum, _MAX_VERSUCHE)
    return False


def _tage_des_monats(speicher: Speicher, schluessel: bytes, jahr: int, monat: int) -> list[Eintrag]:
    praefix = f"{jahr:04d}-{monat:02d}-"
    return [e for e in speicher.eintraege_liste(schluessel, EintragTyp.TAG) if e.zeitraum.startswith(praefix)]


def _monate_des_jahres(speicher: Speicher, schluessel: bytes, jahr: int) -> list[Eintrag]:
    praefix = f"{jahr:04d}-"
    return [e for e in speicher.eintraege_liste(schluessel, EintragTyp.MONAT) if e.zeitraum.startswith(praefix)]


def _text_und_stichpunkte_pruefen(daten: object) -> tuple[str, list[str]] | None:
    if not isinstance(daten, dict):
        return None
    text = daten.get("text")
    punkte = daten.get("stichpunkte")
    if not isinstance(text, str) or not text.strip():
        return None
    if not isinstance(punkte, list):
        return None
    bereinigt = [str(punkt).strip() for punkt in punkte if str(punkt).strip()]
    if not (3 <= len(bereinigt) <= 5):
        return None
    return text.strip(), bereinigt


def veraltete_tage_finden(speicher: Speicher, schluessel: bytes) -> list[str]:
    """Zeiträume aller Tageseinträge, deren Stichpunkte fehlen oder nicht mehr zum Text passen."""
    ergebnis = []
    for eintrag in speicher.eintraege_liste(schluessel, EintragTyp.TAG):
        if not eintrag.text.strip():
            continue
        aktueller_hash = text_hmac(eintrag.text, schluessel)
        if not eintrag.stichpunkte or eintrag.stichpunkte_quelle_hash != aktueller_hash:
            ergebnis.append(eintrag.zeitraum)
    return ergebnis


def _stichpunkte_pruefen(daten: object) -> list[str] | None:
    if not isinstance(daten, dict):
        return None
    punkte = daten.get("stichpunkte")
    if not isinstance(punkte, list):
        return None
    bereinigt = [str(punkt).strip() for punkt in punkte if str(punkt).strip()]
    if not bereinigt or len(bereinigt) > 3:
        return None
    return bereinigt
