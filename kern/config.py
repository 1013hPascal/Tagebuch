"""Konfiguration der App (Format: TOML, Datei config.toml).

DIE MODELLWAHL FÜR ZUSAMMENFASSUNGEN UND SPRACHERKENNUNG STEHT AN DIESER
EINEN STELLE. Der restliche Code kennt keine Modellnamen.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_NAME = "Tagebuch"

# --------------------------------------------------------------------------
# Modelle (einzige Stelle im Code)
# --------------------------------------------------------------------------
DEFAULT_OLLAMA_MODELL = "gemma4:12b"
DEFAULT_WHISPER_MODELL = "small"
# --------------------------------------------------------------------------


def app_dir() -> Path:
    """Datenordner für die verschlüsselte Datenbank und Logs. Mit TAGEBUCH_HOME überschreibbar (Tests)."""
    override = os.environ.get("TAGEBUCH_HOME")
    if override:
        base = Path(override)
    else:
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _config_pfad() -> Path:
    override = os.environ.get("TAGEBUCH_CONFIG")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "config.toml"


def _toml_wert(wert: object) -> str:
    if isinstance(wert, bool):
        return "true" if wert else "false"
    if isinstance(wert, (int, float)):
        return str(wert)
    text = str(wert).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


@dataclass
class Config:
    # Datenbank
    db_pfad: str = ""  # leer = app_dir() / "tagebuch.db"

    # Ollama (Zusammenfassungen)
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_modell: str = DEFAULT_OLLAMA_MODELL
    # Großzügig bemessen, damit eine Jahresübersicht (Eingabe: bis zu zwölf ausführliche
    # Monatsübersichten) nicht am Standard-Kontextfenster von Ollama abgeschnitten wird.
    ollama_num_ctx: int = 8192

    # Whisper (Spracheingabe)
    whisper_modell: str = DEFAULT_WHISPER_MODELL
    whisper_sprache: str = "de"
    max_aufnahme_sekunden: int = 600

    def datenbank_pfad(self) -> Path:
        if self.db_pfad:
            return Path(self.db_pfad)
        return app_dir() / "tagebuch.db"

    @classmethod
    def load(cls, pfad: Path | None = None) -> "Config":
        pfad = pfad or _config_pfad()
        cfg = cls()
        try:
            daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        bekannt = {f.name for f in fields(cls)}
        for schluessel, wert in daten.items():
            if schluessel in bekannt and isinstance(wert, type(getattr(cfg, schluessel))):
                setattr(cfg, schluessel, wert)
        return cfg

    def save(self, pfad: Path | None = None) -> None:
        pfad = pfad or _config_pfad()
        zeilen = [f"{schluessel} = {_toml_wert(wert)}" for schluessel, wert in asdict(self).items()]
        pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
