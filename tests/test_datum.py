"""Tests für kern/datum.py (Abschnitt 8 des Konzepts)."""
from __future__ import annotations

from datetime import date

import pytest

from kern.datum import (
    DatumFehler,
    jahr_anzeigen,
    jahr_parsen,
    monat_anzeigen,
    monat_parsen,
    tag_anzeigen,
    tag_parsen,
)

HEUTE = date(2026, 9, 22)


def test_tag_parsen_mit_fuehrenden_nullen():
    assert tag_parsen("22.09.2026", HEUTE) == "2026-09-22"


def test_tag_parsen_ohne_fuehrende_nullen():
    assert tag_parsen("2.9.2026", HEUTE) == "2026-09-02"


def test_tag_parsen_ungueltiges_datum():
    with pytest.raises(DatumFehler):
        tag_parsen("31.02.2026", HEUTE)


def test_tag_parsen_falsches_format():
    with pytest.raises(DatumFehler):
        tag_parsen("2026-09-22", HEUTE)


def test_tag_parsen_zukunft():
    with pytest.raises(DatumFehler):
        tag_parsen("23.09.2026", HEUTE)


def test_tag_parsen_heute_ist_erlaubt():
    assert tag_parsen("22.09.2026", HEUTE) == "2026-09-22"


def test_monat_parsen():
    assert monat_parsen("09.2026", HEUTE) == "2026-09"


def test_monat_parsen_zukunft():
    with pytest.raises(DatumFehler):
        monat_parsen("10.2026", HEUTE)


def test_monat_parsen_ungueltiger_monat():
    with pytest.raises(DatumFehler):
        monat_parsen("13.2026", HEUTE)


def test_jahr_parsen():
    assert jahr_parsen("2025", HEUTE) == "2025"


def test_jahr_parsen_zukunft():
    with pytest.raises(DatumFehler):
        jahr_parsen("2027", HEUTE)


def test_tag_anzeigen():
    assert tag_anzeigen("2026-09-22") == "Dienstag, 22.09.2026"


def test_monat_anzeigen():
    assert monat_anzeigen("2026-09") == "September 2026"


def test_jahr_anzeigen():
    assert jahr_anzeigen("2025") == "2025"
