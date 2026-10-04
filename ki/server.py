"""Startet und beendet Ollama als Unterprozess (Abschnitt 9 des Konzepts).

So muss Ollama nicht dauerhaft im Hintergrund laufen (z. B. über die Tray-App), sondern nur
während das Tagebuch offen ist - genau wie im Chatbot-Projekt (core/engine.py), von dem dieses
Muster übernommen ist, hier aber ohne dessen GPU-/Leistungs-Einstellungen, die dieses Projekt
nicht braucht.

Läuft schon ein Ollama-Server (z. B. von Hand oder über die Tray-App gestartet), wird er
mitbenutzt und beim Beenden nicht angetastet - nur ein selbst gestarteter Server wird auch
selbst wieder beendet (`owned`).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import psutil

from kern.config import app_dir

log = logging.getLogger(__name__)


def find_ollama_exe() -> Path | None:
    found = shutil.which("ollama")
    if found:
        return Path(found)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        kandidat = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if kandidat.exists():
            return kandidat
    return None


class OllamaServer:
    def __init__(self, host: str) -> None:
        self._host = host
        self._proc: subprocess.Popen | None = None
        self.log_pfad = app_dir() / "logs" / "ollama.log"

    @property
    def owned(self) -> bool:
        """True, wenn dieser Prozess den Server selbst gestartet hat."""
        return self._proc is not None

    def is_running(self) -> bool:
        try:
            return httpx.get(f"{self._host}/api/version", timeout=2).status_code == 200
        except httpx.HTTPError:
            return False

    def start(self, timeout: float = 60) -> None:
        """Startet Ollama, falls es nicht schon läuft, und wartet, bis es antwortet.

        Ist Ollama nicht installiert oder startet es nicht rechtzeitig, kehrt die Methode
        trotzdem zurück (kein Fehler) - die KI bleibt dann einfach nicht erreichbar
        (Abschnitt 9.5 des Konzepts regelt das bereits).
        """
        if self.is_running():
            return
        exe = find_ollama_exe()
        if exe is None:
            log.info("Ollama ist nicht installiert - KI-Zusammenfassungen bleiben aus.")
            return

        self.log_pfad.parent.mkdir(parents=True, exist_ok=True)
        log_datei = open(self.log_pfad, "w", encoding="utf-8")
        self._proc = subprocess.Popen(
            [str(exe), "serve"],
            stdout=log_datei,
            stderr=log_datei,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                log.warning("Ollama wurde beim Start sofort wieder beendet, siehe %s", self.log_pfad)
                self._proc = None
                return
            if self.is_running():
                return
            time.sleep(0.3)
        log.warning("Ollama antwortet nach %s Sekunden immer noch nicht.", timeout)

    def stop(self) -> None:
        """Beendet einen selbst gestarteten Server inklusive Kindprozessen (der Modell-Runner
        läuft als eigener Prozess; `Popen.terminate()` allein würde ihn verwaist zurücklassen)."""
        if self._proc is None:
            return
        try:
            parent = psutil.Process(self._proc.pid)
            for kind in parent.children(recursive=True):
                kind.kill()
            parent.kill()
        except psutil.Error:
            pass
        self._proc = None
