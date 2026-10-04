"""Tests für ki/ollama_client.py."""
from __future__ import annotations

import json

import httpx
import pytest

from ki.ollama_client import OllamaClient, OllamaFehler


class _FakeResponse:
    def __init__(self, inhalt: dict, status_code: int = 200) -> None:
        self._inhalt = inhalt
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Fehler", request=None, response=self)

    def json(self) -> dict:
        return self._inhalt


def test_json_anfrage_gibt_geparste_antwort_zurueck():
    def fake_post(url, *, json, timeout):
        assert url.endswith("/api/chat")
        assert json["format"] == {"type": "object"}
        return _FakeResponse({"message": {"content": '{"stichpunkte": ["a", "b"]}'}})

    client = OllamaClient("http://127.0.0.1:11434", post_fn=fake_post)
    ergebnis = client.json_anfrage(modell="test", system="sys", prompt="frage", schema={"type": "object"})
    assert ergebnis == {"stichpunkte": ["a", "b"]}


def test_verbindungsfehler_wird_zu_ollamafehler():
    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("kein Server", request=None)

    client = OllamaClient("http://127.0.0.1:11434", post_fn=fake_post)
    with pytest.raises(OllamaFehler):
        client.json_anfrage(modell="test", system="sys", prompt="frage", schema={})


def test_ungueltiges_json_loest_valueerror_aus():
    def fake_post(*args, **kwargs):
        return _FakeResponse({"message": {"content": "kein json"}})

    client = OllamaClient("http://127.0.0.1:11434", post_fn=fake_post)
    with pytest.raises(ValueError):
        client.json_anfrage(modell="test", system="sys", prompt="frage", schema={})


def test_num_ctx_wird_als_option_mitgeschickt():
    aufgezeichnet = {}

    def fake_post(url, *, json, timeout):
        aufgezeichnet.update(json)
        return _FakeResponse({"message": {"content": "{}"}})

    client = OllamaClient("http://127.0.0.1:11434", post_fn=fake_post)
    client.json_anfrage(modell="test", system="sys", prompt="frage", schema={}, num_ctx=8192)
    assert aufgezeichnet["options"] == {"num_ctx": 8192}


def test_ohne_num_ctx_keine_optionen_gesetzt():
    aufgezeichnet = {}

    def fake_post(url, *, json, timeout):
        aufgezeichnet.update(json)
        return _FakeResponse({"message": {"content": "{}"}})

    client = OllamaClient("http://127.0.0.1:11434", post_fn=fake_post)
    client.json_anfrage(modell="test", system="sys", prompt="frage", schema={})
    assert "options" not in aufgezeichnet
