"""Tests für ki/server.py (Abschnitt 9.6 des Konzepts): startet/beendet Ollama als
Unterprozess. Alle Tests ersetzen `httpx.get`, `subprocess.Popen` und `psutil.Process` durch
Fakes - es wird nie ein echter Prozess gestartet oder eine echte Netzwerkanfrage gemacht."""
from __future__ import annotations

import httpx
import pytest

from ki import server as server_modul
from ki.server import OllamaServer, find_ollama_exe


@pytest.fixture(autouse=True)
def _app_dir_isoliert(tmp_path, monkeypatch):
    """`OllamaServer.__init__` liest `app_dir()` für den Log-Pfad - ohne Umleitung würde das
    echte `%APPDATA%\\Tagebuch` auf dem Testrechner angelegt."""
    monkeypatch.setenv("TAGEBUCH_HOME", str(tmp_path))


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeProc:
    def __init__(self, laeuft_sofort_weiter: bool = True) -> None:
        self.pid = 4242
        self._laeuft = laeuft_sofort_weiter
        self.terminiert = False

    def poll(self):
        return None if self._laeuft else 1

    def kill(self) -> None:
        self.terminiert = True


def test_is_running_true_bei_erfolgreicher_antwort(monkeypatch):
    monkeypatch.setattr(server_modul.httpx, "get", lambda url, timeout: _FakeResponse(200))
    assert OllamaServer("http://127.0.0.1:11434").is_running() is True


def test_is_running_false_bei_verbindungsfehler(monkeypatch):
    def kaputt(url, timeout):
        raise httpx.ConnectError("nein")

    monkeypatch.setattr(server_modul.httpx, "get", kaputt)
    assert OllamaServer("http://127.0.0.1:11434").is_running() is False


def test_start_tut_nichts_wenn_schon_erreichbar(monkeypatch):
    monkeypatch.setattr(server_modul.httpx, "get", lambda url, timeout: _FakeResponse(200))
    aufrufe = []
    monkeypatch.setattr(server_modul.subprocess, "Popen", lambda *a, **k: aufrufe.append(1))

    s = OllamaServer("http://127.0.0.1:11434")
    s.start()

    assert aufrufe == []
    assert s.owned is False


def test_start_ohne_installiertes_ollama_tut_nichts(monkeypatch):
    monkeypatch.setattr(server_modul.httpx, "get", lambda url, timeout: (_ for _ in ()).throw(httpx.ConnectError("x")))
    monkeypatch.setattr(server_modul, "find_ollama_exe", lambda: None)
    aufrufe = []
    monkeypatch.setattr(server_modul.subprocess, "Popen", lambda *a, **k: aufrufe.append(1))

    s = OllamaServer("http://127.0.0.1:11434")
    s.start()

    assert aufrufe == []
    assert s.owned is False


def test_start_startet_prozess_und_wartet_bis_erreichbar(monkeypatch, tmp_path):
    monkeypatch.setattr(server_modul, "find_ollama_exe", lambda: tmp_path / "ollama.exe")

    antworten = iter([False, False, True])  # erst nicht erreichbar, dann ja

    def fake_get(url, timeout):
        if next(antworten):
            return _FakeResponse(200)
        raise httpx.ConnectError("noch nicht")

    monkeypatch.setattr(server_modul.httpx, "get", fake_get)
    monkeypatch.setattr(server_modul.time, "sleep", lambda s: None)

    proc = _FakeProc()
    monkeypatch.setattr(server_modul.subprocess, "Popen", lambda *a, **k: proc)

    s = OllamaServer("http://127.0.0.1:11434")
    s.start()

    assert s.owned is True
    assert s.log_pfad.exists()


def test_start_gibt_auf_wenn_prozess_sofort_endet(monkeypatch, tmp_path):
    monkeypatch.setattr(server_modul, "find_ollama_exe", lambda: tmp_path / "ollama.exe")
    monkeypatch.setattr(
        server_modul.httpx, "get", lambda url, timeout: (_ for _ in ()).throw(httpx.ConnectError("x"))
    )
    monkeypatch.setattr(server_modul.subprocess, "Popen", lambda *a, **k: _FakeProc(laeuft_sofort_weiter=False))

    s = OllamaServer("http://127.0.0.1:11434")
    s.start()

    assert s.owned is False  # Prozess wurde sofort wieder beendet -> nicht als "eigen" gezählt


def test_stop_ohne_gestarteten_prozess_tut_nichts():
    s = OllamaServer("http://127.0.0.1:11434")
    s.stop()  # darf nicht abstürzen
    assert s.owned is False


def test_stop_beendet_eigenen_prozess_und_kinder(monkeypatch, tmp_path):
    monkeypatch.setattr(server_modul, "find_ollama_exe", lambda: tmp_path / "ollama.exe")

    antworten = iter([False, True])  # erst nicht erreichbar (start() soll den Prozess spawnen), dann ja

    def fake_get(url, timeout):
        if next(antworten):
            return _FakeResponse(200)
        raise httpx.ConnectError("noch nicht")

    monkeypatch.setattr(server_modul.httpx, "get", fake_get)
    proc = _FakeProc()
    monkeypatch.setattr(server_modul.subprocess, "Popen", lambda *a, **k: proc)

    kinder = [_FakeProc(), _FakeProc()]

    class _FakePsutilProc:
        def __init__(self, pid) -> None:
            assert pid == proc.pid

        def children(self, recursive=True):
            return kinder

        def kill(self) -> None:
            proc.terminiert = True

    monkeypatch.setattr(server_modul.psutil, "Process", _FakePsutilProc)

    s = OllamaServer("http://127.0.0.1:11434")
    s.start()
    assert s.owned is True

    s.stop()

    assert proc.terminiert is True
    assert all(kind.terminiert for kind in kinder)
    assert s.owned is False


def test_find_ollama_exe_nutzt_localappdata_wenn_nicht_im_pfad(monkeypatch, tmp_path):
    monkeypatch.setattr(server_modul.shutil, "which", lambda name: None)
    ordner = tmp_path / "Programs" / "Ollama"
    ordner.mkdir(parents=True)
    exe = ordner / "ollama.exe"
    exe.write_text("")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert find_ollama_exe() == exe


def test_find_ollama_exe_none_wenn_nirgends_gefunden(monkeypatch, tmp_path):
    monkeypatch.setattr(server_modul.shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # leer, keine Ollama-Installation

    assert find_ollama_exe() is None
