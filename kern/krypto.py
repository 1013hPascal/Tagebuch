"""Verschlüsselung (Abschnitt 5 des Konzepts).

Aus dem Passwort wird mit Scrypt ein 256-Bit-Schlüssel abgeleitet. Jedes
verschlüsselte Feld wird mit AES-GCM und einer eigenen zufälligen Nonce
verschlüsselt. Der Schlüssel existiert nur im Arbeitsspeicher, solange das
Programm läuft.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT_LAENGE = 16
NONCE_LAENGE = 12
SCHLUESSEL_LAENGE = 32  # 256 Bit

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

_PRUEFTEXT = b"tagebuch-pruefung"


class FalschesPasswort(Exception):
    """Das Passwort passt nicht zum gespeicherten Prüftext, oder die Daten sind beschädigt."""


@dataclass(frozen=True)
class KdfParameter:
    n: int = SCRYPT_N
    r: int = SCRYPT_R
    p: int = SCRYPT_P

    def als_text(self) -> str:
        return f"{self.n}:{self.r}:{self.p}"

    @classmethod
    def aus_text(cls, text: str) -> "KdfParameter":
        n, r, p = (int(teil) for teil in text.split(":"))
        return cls(n=n, r=r, p=p)


def neues_salt() -> bytes:
    return os.urandom(SALT_LAENGE)


def schluessel_ableiten(passwort: str, salt: bytes, parameter: KdfParameter = KdfParameter()) -> bytes:
    """Leitet aus dem Passwort einen 256-Bit-Schlüssel ab."""
    kdf = Scrypt(salt=salt, length=SCHLUESSEL_LAENGE, n=parameter.n, r=parameter.r, p=parameter.p)
    return kdf.derive(passwort.encode("utf-8"))


def verifier_erstellen(schluessel: bytes) -> bytes:
    """Verschlüsselt den festen Prüftext; wird in meta.verifier gespeichert."""
    return verschluesseln(_PRUEFTEXT, schluessel)


def verifier_pruefen(schluessel: bytes, verifier: bytes) -> bool:
    """True, wenn sich der Prüftext mit diesem Schlüssel entschlüsseln lässt."""
    try:
        return entschluesseln(verifier, schluessel) == _PRUEFTEXT
    except FalschesPasswort:
        return False


def verschluesseln(klartext: bytes, schluessel: bytes) -> bytes:
    """Verschlüsselt mit AES-GCM und eigener Nonce. Rückgabe: Nonce + Chiffrat."""
    nonce = os.urandom(NONCE_LAENGE)
    chiffrat = AESGCM(schluessel).encrypt(nonce, klartext, None)
    return nonce + chiffrat


def entschluesseln(daten: bytes, schluessel: bytes) -> bytes:
    """Trennt Nonce vom Chiffrat und entschlüsselt. Löst FalschesPasswort bei Fehlschlag aus."""
    if len(daten) < NONCE_LAENGE:
        raise FalschesPasswort("Daten zu kurz für eine Nonce.")
    nonce, chiffrat = daten[:NONCE_LAENGE], daten[NONCE_LAENGE:]
    try:
        return AESGCM(schluessel).decrypt(nonce, chiffrat, None)
    except InvalidTag as exc:
        raise FalschesPasswort("Entschlüsselung fehlgeschlagen.") from exc


def text_verschluesseln(text: str, schluessel: bytes) -> bytes:
    return verschluesseln(text.encode("utf-8"), schluessel)


def text_entschluesseln(daten: bytes, schluessel: bytes) -> str:
    return entschluesseln(daten, schluessel).decode("utf-8")


def text_hmac(text: str, schluessel: bytes) -> str:
    """HMAC über den Klartext, um veraltete Stichpunkte zu erkennen (Abschnitt 6, Empfehlung statt
    einfachem Hash: verrät ohne den Schlüssel nicht, ob sich zwei Texte gleichen)."""
    teilschluessel = hashlib.sha256(schluessel + b"tagebuch-hmac-teilschluessel").digest()
    return hmac.new(teilschluessel, text.encode("utf-8"), hashlib.sha256).hexdigest()
