"""Mikrofonaufnahme (Abschnitt 7.3 des Konzepts).

Aufnahmen werden nie auf die Festplatte geschrieben, nur im Arbeitsspeicher
gehalten, bis die Umwandlung in Text fertig ist (Abschnitt 5, Datenschutz).
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd

ABTASTRATE = 16000  # Hz - was faster-whisper erwartet


class AufnahmeFehler(Exception):
    """Kein Mikrofon gefunden oder ein anderer Aufnahmefehler."""


class Aufnahme:
    """Nimmt Audio vom Standardmikrofon auf, bis stop() aufgerufen wird oder
    die maximale Dauer erreicht ist (Abschnitt 7.3: „automatisch beenden“)."""

    def __init__(self, max_sekunden: int) -> None:
        self._max_frames = max_sekunden * ABTASTRATE
        self._bloecke: list[np.ndarray] = []
        self._frames = 0
        self._voll = False
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=ABTASTRATE, channels=1, dtype="float32", callback=self._callback
            )
            self._stream.start()
        except Exception as exc:  # sd.PortAudioError o.ä., je nach Plattform/Treiber
            self._stream = None
            raise AufnahmeFehler(f"Kein Mikrofon verfügbar: {exc}") from exc

    def _callback(self, indata, frames, time_info, status) -> None:
        if self._voll:
            return
        self._bloecke.append(indata[:, 0].copy())
        self._frames += frames
        if self._frames >= self._max_frames:
            self._voll = True

    def ist_voll(self) -> bool:
        return self._voll

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._bloecke:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self._bloecke)
        return audio[: self._max_frames]
