"""SQLite-Speicher (Abschnitt 5 und 6 des Konzepts).

Die Datei enthält nur Chiffrat. Nur `typ` und `zeitraum` bleiben lesbar, damit
sortiert werden kann, ohne den Schlüssel zu benötigen: Wer die Datei hat,
sieht, an welchen Tagen es Einträge gibt, aber nicht deren Inhalt.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from .krypto import (
    FalschesPasswort,
    KdfParameter,
    neues_salt,
    schluessel_ableiten,
    text_entschluesseln,
    text_verschluesseln,
    verifier_erstellen,
    verifier_pruefen,
)
from .modelle import Eintrag, EintragTyp, Suchtreffer

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value BLOB
);
CREATE TABLE IF NOT EXISTS eintraege (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    typ TEXT NOT NULL,
    zeitraum TEXT NOT NULL,
    text_enc BLOB NOT NULL,
    stichpunkte_enc BLOB,
    stichpunkte_quelle_hash TEXT,
    manuell_bearbeitet INTEGER NOT NULL DEFAULT 0,
    erstellt_am TEXT NOT NULL,
    geaendert_am TEXT NOT NULL,
    UNIQUE(typ, zeitraum)
);
"""


class NichtEingerichtet(Exception):
    """Es gibt noch keinen Account (keine passenden Einträge in meta)."""


class BereitsEingerichtet(Exception):
    """Es existiert schon ein Account; kann nicht erneut eingerichtet werden."""


class Speicher:
    """Verwaltet eine verschlüsselte Tagebuch-Datenbank."""

    def __init__(self, pfad: Path) -> None:
        self.pfad = pfad
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(pfad), check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def ist_eingerichtet(self) -> bool:
        with self._lock:
            zeile = self._conn.execute("SELECT value FROM meta WHERE key = 'verifier'").fetchone()
            return zeile is not None

    def einrichten(self, passwort: str) -> bytes:
        """Legt einen neuen Account an. Löst BereitsEingerichtet aus, falls schon einer existiert."""
        with self._lock:
            if self.ist_eingerichtet():
                raise BereitsEingerichtet("Es gibt bereits einen Account.")
            salt = neues_salt()
            parameter = KdfParameter()
            schluessel = schluessel_ableiten(passwort, salt, parameter)
            verifier = verifier_erstellen(schluessel)
            with self._conn:
                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION).encode("utf-8")),
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("kdf_salt", salt)
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("kdf_params", parameter.als_text().encode("utf-8")),
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("verifier", verifier)
                )
            return schluessel

    def anmelden(self, passwort: str) -> bytes:
        """Prüft das Passwort und gibt bei Erfolg den Schlüssel zurück.

        Löst NichtEingerichtet aus, wenn noch kein Account existiert, und
        FalschesPasswort, wenn das Passwort nicht passt.
        """
        with self._lock:
            if not self.ist_eingerichtet():
                raise NichtEingerichtet("Es gibt noch keinen Account.")
            salt = self._meta_holen("kdf_salt")
            parameter = KdfParameter.aus_text(self._meta_holen("kdf_params").decode("utf-8"))
            verifier = self._meta_holen("verifier")
            schluessel = schluessel_ableiten(passwort, salt, parameter)
            if not verifier_pruefen(schluessel, verifier):
                raise FalschesPasswort("Das Passwort ist nicht richtig.")
            return schluessel

    def passwort_aendern(self, schluessel_alt: bytes, neues_passwort: str) -> bytes:
        """Verschlüsselt alle Einträge neu, in einer einzigen Transaktion (Abschnitt 5)."""
        with self._lock:
            zeilen = self._conn.execute(
                "SELECT id, text_enc, stichpunkte_enc FROM eintraege"
            ).fetchall()
            entschluesselt = [
                (
                    eintrag_id,
                    text_entschluesseln(text_enc, schluessel_alt),
                    text_entschluesseln(stichpunkte_enc, schluessel_alt) if stichpunkte_enc is not None else None,
                )
                for eintrag_id, text_enc, stichpunkte_enc in zeilen
            ]

            salt = neues_salt()
            parameter = KdfParameter()
            schluessel_neu = schluessel_ableiten(neues_passwort, salt, parameter)
            verifier = verifier_erstellen(schluessel_neu)

            with self._conn:
                for eintrag_id, text, stichpunkte in entschluesselt:
                    text_enc = text_verschluesseln(text, schluessel_neu)
                    stichpunkte_enc = (
                        text_verschluesseln(stichpunkte, schluessel_neu) if stichpunkte is not None else None
                    )
                    self._conn.execute(
                        "UPDATE eintraege SET text_enc = ?, stichpunkte_enc = ? WHERE id = ?",
                        (text_enc, stichpunkte_enc, eintrag_id),
                    )
                self._conn.execute("UPDATE meta SET value = ? WHERE key = 'kdf_salt'", (salt,))
                self._conn.execute(
                    "UPDATE meta SET value = ? WHERE key = 'kdf_params'",
                    (parameter.als_text().encode("utf-8"),),
                )
                self._conn.execute("UPDATE meta SET value = ? WHERE key = 'verifier'", (verifier,))
            return schluessel_neu

    def account_loeschen(self) -> None:
        """Löscht die gesamte Datenbankdatei unwiderruflich (Abschnitt 5, „Account löschen“)."""
        with self._lock:
            self._conn.close()
        self.pfad.unlink(missing_ok=True)

    def _meta_holen(self, key: str) -> bytes:
        zeile = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if zeile is None:
            raise NichtEingerichtet(f"meta-Eintrag '{key}' fehlt.")
        return zeile[0]

    # ------------------------------------------------------------------
    # Einträge
    # ------------------------------------------------------------------

    def eintrag_speichern(
        self,
        schluessel: bytes,
        typ: EintragTyp,
        zeitraum: str,
        text: str,
        *,
        anhaengen: bool = False,
    ) -> None:
        """Legt einen Eintrag an oder aktualisiert ihn. Bei anhaengen=True wird der Text unten angehängt."""
        with self._lock:
            vorhanden = self._conn.execute(
                "SELECT id, text_enc FROM eintraege WHERE typ = ? AND zeitraum = ?",
                (typ.value, zeitraum),
            ).fetchone()
            jetzt = datetime.now().isoformat(timespec="seconds")
            with self._conn:
                if vorhanden is None:
                    text_enc = text_verschluesseln(text, schluessel)
                    self._conn.execute(
                        "INSERT INTO eintraege (typ, zeitraum, text_enc, manuell_bearbeitet, "
                        "erstellt_am, geaendert_am) VALUES (?, ?, ?, 0, ?, ?)",
                        (typ.value, zeitraum, text_enc, jetzt, jetzt),
                    )
                else:
                    eintrag_id, alter_text_enc = vorhanden
                    if anhaengen:
                        alter_text = text_entschluesseln(alter_text_enc, schluessel)
                        trenner = "\n\n" if alter_text else ""
                        text = alter_text + trenner + text
                    text_enc = text_verschluesseln(text, schluessel)
                    self._conn.execute(
                        "UPDATE eintraege SET text_enc = ?, geaendert_am = ? WHERE id = ?",
                        (text_enc, jetzt, eintrag_id),
                    )

    def eintrag_laden(self, schluessel: bytes, typ: EintragTyp, zeitraum: str) -> Eintrag | None:
        with self._lock:
            zeile = self._conn.execute(
                "SELECT id, text_enc, stichpunkte_enc, stichpunkte_quelle_hash, "
                "manuell_bearbeitet, erstellt_am, geaendert_am "
                "FROM eintraege WHERE typ = ? AND zeitraum = ?",
                (typ.value, zeitraum),
            ).fetchone()
            if zeile is None:
                return None
            return self._zeile_zu_eintrag(typ, zeitraum, zeile, schluessel)

    def eintraege_liste(self, schluessel: bytes, typ: EintragTyp) -> list[Eintrag]:
        """Alle Einträge eines Typs, neuester zuerst."""
        with self._lock:
            zeilen = self._conn.execute(
                "SELECT id, zeitraum, text_enc, stichpunkte_enc, stichpunkte_quelle_hash, "
                "manuell_bearbeitet, erstellt_am, geaendert_am "
                "FROM eintraege WHERE typ = ? ORDER BY zeitraum DESC",
                (typ.value,),
            ).fetchall()
            return [
                self._zeile_zu_eintrag(typ, zeile[1], (zeile[0],) + zeile[2:], schluessel)
                for zeile in zeilen
            ]

    def eintrag_loeschen(self, typ: EintragTyp, zeitraum: str) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "DELETE FROM eintraege WHERE typ = ? AND zeitraum = ?", (typ.value, zeitraum)
                )

    def stichpunkte_speichern(
        self, schluessel: bytes, typ: EintragTyp, zeitraum: str, stichpunkte: str, quelle_hash: str
    ) -> None:
        with self._lock:
            stichpunkte_enc = text_verschluesseln(stichpunkte, schluessel)
            with self._conn:
                self._conn.execute(
                    "UPDATE eintraege SET stichpunkte_enc = ?, stichpunkte_quelle_hash = ? "
                    "WHERE typ = ? AND zeitraum = ?",
                    (stichpunkte_enc, quelle_hash, typ.value, zeitraum),
                )

    def manuell_bearbeitet_setzen(self, typ: EintragTyp, zeitraum: str, wert: bool) -> None:
        """Nur für Monat und Jahr relevant (Abschnitt 6 und 9.4)."""
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "UPDATE eintraege SET manuell_bearbeitet = ? WHERE typ = ? AND zeitraum = ?",
                    (int(wert), typ.value, zeitraum),
                )

    def last_run_date_setzen(self, datum_iso: str) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_run_date', ?)",
                    (datum_iso.encode("utf-8"),),
                )

    def last_run_date_holen(self) -> str | None:
        with self._lock:
            zeile = self._conn.execute("SELECT value FROM meta WHERE key = 'last_run_date'").fetchone()
            return zeile[0].decode("utf-8") if zeile is not None else None

    def suchen(self, schluessel: bytes, suchbegriff: str) -> list[Suchtreffer]:
        """Durchsucht Text und Stichpunkte aller Einträge, ohne Beachtung von Groß-/
        Kleinschreibung, über Tage, Monate und Jahre (Abschnitt 7.6). Da alles
        verschlüsselt ist, geschieht das im Arbeitsspeicher - für ein Tagebuch schnell
        genug. Neueste zuerst.
        """
        ziel = suchbegriff.lower()
        treffer: list[Suchtreffer] = []
        for typ in (EintragTyp.TAG, EintragTyp.MONAT, EintragTyp.JAHR):
            for eintrag in self.eintraege_liste(schluessel, typ):
                if ziel in eintrag.text.lower():
                    quelle = eintrag.text
                elif ziel in eintrag.stichpunkte.lower():
                    quelle = eintrag.stichpunkte
                else:
                    continue
                treffer.append(Suchtreffer(eintrag, _ausschnitt_um_treffer(quelle, suchbegriff)))
        treffer.sort(key=lambda t: t.eintrag.zeitraum, reverse=True)
        return treffer

    def _zeile_zu_eintrag(self, typ: EintragTyp, zeitraum: str, zeile: tuple, schluessel: bytes) -> Eintrag:
        (eintrag_id, text_enc, stichpunkte_enc, quelle_hash, manuell, erstellt_am, geaendert_am) = zeile
        text = text_entschluesseln(text_enc, schluessel)
        stichpunkte = text_entschluesseln(stichpunkte_enc, schluessel) if stichpunkte_enc is not None else ""
        return Eintrag(
            id=eintrag_id,
            typ=typ,
            zeitraum=zeitraum,
            text=text,
            stichpunkte=stichpunkte,
            stichpunkte_quelle_hash=quelle_hash or "",
            manuell_bearbeitet=bool(manuell),
            erstellt_am=datetime.fromisoformat(erstellt_am),
            geaendert_am=datetime.fromisoformat(geaendert_am),
        )


def _ausschnitt_um_treffer(text: str, suchbegriff: str, breite: int = 60) -> str:
    """Kurzer Textausschnitt rund um die erste Fundstelle (Abschnitt 7.6)."""
    index = text.lower().find(suchbegriff.lower())
    if index == -1:
        return ""
    start = max(0, index - breite)
    ende = min(len(text), index + len(suchbegriff) + breite)
    stueck = text[start:ende].strip()
    praefix = "… " if start > 0 else ""
    suffix = " …" if ende < len(text) else ""
    return f"{praefix}{stueck}{suffix}"
