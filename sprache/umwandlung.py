"""Spracherkennung mit faster-whisper (Abschnitt 4 des Konzepts).

Das Modell wird beim ersten Gebrauch geladen und danach im Speicher gehalten
(Abschnitt 7.3). Läuft auf der CPU mit int8, da auf dem Zielsystem kein CUDA
zur Verfügung steht (Abschnitt 3). Sprache ist fest auf Deutsch eingestellt.
"""
from __future__ import annotations

import logging
import threading

import numpy as np

log = logging.getLogger(__name__)

_modell = None
_modell_name: str | None = None
_lock = threading.Lock()


def _modell_laden(name: str):
    global _modell, _modell_name
    with _lock:
        if _modell is None or _modell_name != name:
            from faster_whisper import WhisperModel

            log.info("Lade Whisper-Modell '%s' ...", name)
            _modell = WhisperModel(name, device="cpu", compute_type="int8")
            _modell_name = name
            log.info("Whisper-Modell '%s' geladen.", name)
        return _modell


def transkribieren(audio: np.ndarray, *, modell_name: str, sprache: str = "de") -> str:
    """Wandelt aufgenommenes Audio (float32, 16 kHz, mono) in Text um."""
    if audio.size == 0:
        return ""
    modell = _modell_laden(modell_name)
    segmente, _info = modell.transcribe(audio, language=sprache)
    teile = [segment.text.strip() for segment in segmente]
    return " ".join(teil for teil in teile if teil).strip()
