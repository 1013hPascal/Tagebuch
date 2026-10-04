"""Tests für kern/krypto.py."""
from __future__ import annotations

import os

import pytest

from kern.krypto import (
    FalschesPasswort,
    KdfParameter,
    entschluesseln,
    neues_salt,
    schluessel_ableiten,
    text_entschluesseln,
    text_hmac,
    text_verschluesseln,
    verifier_erstellen,
    verifier_pruefen,
    verschluesseln,
)

_SCHNELLE_PARAMETER = KdfParameter(n=2**10, r=8, p=1)  # klein, nur damit die Tests schnell laufen


def test_schluessel_ist_reproduzierbar():
    salt = neues_salt()
    a = schluessel_ableiten("geheim", salt, _SCHNELLE_PARAMETER)
    b = schluessel_ableiten("geheim", salt, _SCHNELLE_PARAMETER)
    assert a == b
    assert len(a) == 32


def test_verschiedene_passwoerter_ergeben_verschiedene_schluessel():
    salt = neues_salt()
    a = schluessel_ableiten("geheim", salt, _SCHNELLE_PARAMETER)
    b = schluessel_ableiten("anders", salt, _SCHNELLE_PARAMETER)
    assert a != b


def test_verschluesseln_und_entschluesseln():
    schluessel = os.urandom(32)
    daten = verschluesseln(b"Hallo Tagebuch", schluessel)
    assert entschluesseln(daten, schluessel) == b"Hallo Tagebuch"


def test_text_verschluesseln_roundtrip_mit_umlauten():
    schluessel = os.urandom(32)
    daten = text_verschluesseln("Ein Test mit Umlauten: äöü ß", schluessel)
    assert text_entschluesseln(daten, schluessel) == "Ein Test mit Umlauten: äöü ß"


def test_falscher_schluessel_schlaegt_fehl():
    schluessel = os.urandom(32)
    anderer = os.urandom(32)
    daten = verschluesseln(b"geheim", schluessel)
    with pytest.raises(FalschesPasswort):
        entschluesseln(daten, anderer)


def test_verifier_erkennt_richtiges_passwort():
    schluessel = os.urandom(32)
    verifier = verifier_erstellen(schluessel)
    assert verifier_pruefen(schluessel, verifier) is True


def test_verifier_erkennt_falsches_passwort():
    schluessel = os.urandom(32)
    anderer = os.urandom(32)
    verifier = verifier_erstellen(schluessel)
    assert verifier_pruefen(anderer, verifier) is False


def test_kdf_parameter_text_roundtrip():
    parameter = KdfParameter(n=2**14, r=8, p=1)
    assert KdfParameter.aus_text(parameter.als_text()) == parameter


def test_hmac_ist_gleich_bei_gleichem_text_und_schluessel():
    schluessel = os.urandom(32)
    a = text_hmac("Heute war ein guter Tag.", schluessel)
    b = text_hmac("Heute war ein guter Tag.", schluessel)
    assert a == b


def test_hmac_unterscheidet_sich_bei_anderem_schluessel():
    text = "Heute war ein guter Tag."
    a = text_hmac(text, os.urandom(32))
    b = text_hmac(text, os.urandom(32))
    assert a != b
