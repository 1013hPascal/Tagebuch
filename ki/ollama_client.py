"""Ollama-Anbindung für die KI-Zusammenfassungen (Abschnitt 4 und 9 des Konzepts).

Angelehnt an das Chatbot-Projekt: eigener Client über httpx, klare Fehlerklasse.
Anders als der Chatbot fordert dieser Client kein freies Streaming an, sondern
eine einzelne, strukturierte JSON-Antwort (Ollama-Option `format`).
"""
from __future__ import annotations

import json
import logging
from typing import Callable

import httpx

log = logging.getLogger(__name__)

# Große Modelle (z. B. gemma4:12b) brauchen nach einem frischen Ollama-Start oder wenn sie
# aus dem Speicher entladen wurden, erst einmal Zeit zum Laden (mehrere GB von der Platte) -
# das kann deutlich länger dauern als eine "normale" Anfrage. Großzügig bemessen, damit ein
# solcher Kaltstart nicht vorzeitig abbricht.
ANFRAGE_TIMEOUT_S = 120
# Beim Beenden des Programms wird auf eine noch laufende Anfrage gewartet (Abschnitt 9), statt
# den Hintergrund-Thread mitten in der Ausführung zu zerstören - etwas großzügiger als
# ANFRAGE_TIMEOUT_S selbst, damit eine Anfrage, die genau an ihrem eigenen Timeout hängt, noch
# sauber mit einem Fehler zurückkommt, statt vom Warten abgeschnitten zu werden.
WARTE_TIMEOUT_MS = (ANFRAGE_TIMEOUT_S + 10) * 1000


class OllamaFehler(Exception):
    """Ollama ist nicht erreichbar oder hat einen Fehler gemeldet."""


class OllamaClient:
    def __init__(self, host: str, *, post_fn: Callable[..., httpx.Response] = httpx.post) -> None:
        self._host = host
        self._post_fn = post_fn

    def json_anfrage(
        self, *, modell: str, system: str, prompt: str, schema: dict, num_ctx: int | None = None
    ) -> dict:
        """Fragt das Modell mit erzwungenem JSON-Format ab und gibt das geparste Ergebnis zurück.

        `num_ctx` vergrößert bei Bedarf das Kontextfenster (Standard von Ollama reicht für
        lange Eingaben wie eine Jahresübersicht sonst unter Umständen nicht aus).
        """
        anfrage = {
            "model": modell,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "format": schema,
            "stream": False,
        }
        if num_ctx is not None:
            anfrage["options"] = {"num_ctx": num_ctx}
        try:
            antwort = self._post_fn(
                f"{self._host}/api/chat",
                json=anfrage,
                timeout=httpx.Timeout(ANFRAGE_TIMEOUT_S, connect=5),
            )
            antwort.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaFehler("Ollama ist nicht erreichbar.") from exc
        except httpx.HTTPError as exc:
            raise OllamaFehler(f"Ollama-Anfrage fehlgeschlagen: {exc}") from exc

        daten = antwort.json()
        inhalt = daten.get("message", {}).get("content", "")
        try:
            return json.loads(inhalt)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Antwort war kein gültiges JSON.") from exc
