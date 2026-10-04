"""Tests für ui/hauptfenster.py: die Verdrahtung der Ansichten, Menüs und der
KI-Warteschlange (Abschnitt 7, 9 und 10 des Konzepts). Nutzt einen Fake-Ollama-Client,
damit keine echte Anfrage nötig ist."""
from __future__ import annotations

from datetime import date

from kern.config import Config
from kern.modelle import EintragTyp
from ui.hauptfenster import HauptFenster


class FakeClient:
    """Antwortet sofort, ohne echtes Ollama zu brauchen."""

    def json_anfrage(self, *, modell, system, prompt, schema, num_ctx=None):
        eigenschaften = schema.get("properties", {})
        if "text" in eigenschaften:
            return {"text": "Eine ausführliche Übersicht mit mehreren Sätzen Inhalt.", "stichpunkte": ["a", "b", "c"]}
        if "antwort" in eigenschaften:
            return {"antwort": "Die Antwort auf die Frage."}
        return {"stichpunkte": ["Ein Punkt"]}


class FakeServer:
    """Ersetzt ki.server.OllamaServer in Tests: kein echter Unterprozess, kein echtes Netzwerk."""

    def __init__(self) -> None:
        self.gestartet = False
        self.gestoppt = False
        self.owned = False

    def start(self, timeout: float = 60) -> None:
        self.gestartet = True

    def stop(self) -> None:
        self.gestoppt = True


def _bauen(speicher, schluessel, qtbot) -> HauptFenster:
    fenster = HauptFenster(Config(), speicher, schluessel)
    fenster._ollama_client = FakeClient()
    fenster._ollama_server = FakeServer()
    qtbot.addWidget(fenster)
    # Lässt den beim Start geplanten Hintergrund-Check (QTimer.singleShot(0, ...)) jetzt
    # ablaufen, statt ihn ungenutzt stehen zu lassen und so einem späteren Test in die
    # Quere kommen zu lassen.
    qtbot.wait(50)
    return fenster


def test_menue_datei_eintraege(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)

    datei_menu = fenster.menuBar().actions()[0].menu()
    eintraege = {a.text(): a for a in datei_menu.actions() if a.text()}
    assert list(eintraege) == ["Suche/Frage", "Passwort ändern", "Account löschen", "Beenden"]
    assert eintraege["Suche/Frage"].shortcut().toString() == "Ctrl+F"
    assert eintraege["Beenden"].shortcut().toString() == "Ctrl+Q"


def test_menue_rueckschau_eintraege(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)

    rueckschau_menu = fenster.menuBar().actions()[1].menu()
    texte = [a.text() for a in rueckschau_menu.actions() if a.text()]
    assert texte == ["Tagesübersicht", "Monatsübersicht", "Jahresübersicht"]
    assert fenster._rueckschau_aktionen[EintragTyp.TAG].isChecked() is True


def test_start_zeigt_tagesuebersicht(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    assert fenster._stapel.currentWidget() is fenster._uebersicht
    assert fenster._aktueller_typ == EintragTyp.TAG


def test_start_startet_ollama_server_im_hintergrund(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    assert fenster._ollama_server.gestartet is True
    assert fenster._server_start_task is None


def test_close_event_stoppt_ollama_server(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    fenster.close()
    assert fenster._ollama_server.gestoppt is True


def test_rueckschau_wechseln(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)

    fenster._rueckschau_aktionen[EintragTyp.MONAT].trigger()
    assert fenster._aktueller_typ == EintragTyp.MONAT
    assert fenster._stapel.currentWidget() is fenster._uebersicht


def test_speichern_ueber_editor_erzeugt_ki_auftrag(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    heute = date.today()

    fenster._uebersicht._eintrag_aktivieren(fenster._uebersicht.liste.item(0))
    assert fenster._stapel.currentWidget() is fenster._editor

    fenster._editor.text_feld.setPlainText("Ein ereignisreicher Tag.")
    fenster._editor.speichern_knopf.click()

    assert fenster._stapel.currentWidget() is fenster._uebersicht
    qtbot.waitUntil(
        lambda: speicher.eintrag_laden(schluessel, EintragTyp.TAG, heute.isoformat()).stichpunkte != "",
        timeout=2000,
    )
    fenster._ki_worker.abbrechen_und_warten()


def test_suche_oeffnet_ergebnisansicht(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Ein Urlaub in Italien.")
    fenster = _bauen(speicher, schluessel, qtbot)

    treffer = speicher.suchen(schluessel, "Urlaub")
    fenster._suche.anzeigen("Urlaub", treffer)
    fenster._stapel.setCurrentWidget(fenster._suche)

    assert fenster._stapel.currentWidget() is fenster._suche
    assert fenster._suche.liste.item(0).text() == "Suchergebnisse für „Urlaub“: 1 Treffer"

    fenster._suche.zurueck.emit()
    assert fenster._stapel.currentWidget() is fenster._uebersicht


class _FakeSuchDialog:
    """Ersetzt den echten (modalen) SuchDialog in Tests: liefert einen festen Suchbegriff,
    ohne ein Dialogfenster zu öffnen."""

    def __init__(self, suchbegriff: str) -> None:
        self.suchbegriff = suchbegriff

    def exec(self) -> bool:
        return True


def test_bearbeiten_vergangener_tag_hat_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Alter Text")
    fenster = _bauen(speicher, schluessel, qtbot)

    fenster._bearbeiten_von_leseansicht(EintragTyp.TAG, "2020-01-01")

    assert fenster._stapel.currentWidget() is fenster._editor
    assert fenster._editor.sprache_knopf.isHidden() is False


def test_bearbeiten_monatsuebersicht_hat_keine_spracheingabe(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Übersicht")
    fenster = _bauen(speicher, schluessel, qtbot)

    fenster._bearbeiten_von_leseansicht(EintragTyp.MONAT, "2026-08")

    assert fenster._editor.sprache_knopf.isHidden() is True


def test_suchbegriff_ohne_fragezeichen_ruft_ki_nicht_auf(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2020-01-01", "Ein Urlaub in Italien.")
    fenster = _bauen(speicher, schluessel, qtbot)

    monkeypatch.setattr("ui.hauptfenster.SuchDialog", lambda parent: _FakeSuchDialog("Urlaub"))
    fenster._suchen_oeffnen()

    assert fenster._frage_task is None
    assert fenster._suche.ki_antwort.isHidden() is True


def test_suchen_oeffnen_mit_fragezeichen_stoesst_frage_an(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Ein Urlaub in Italien.")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Urlaub in Italien", "hash")
    fenster = _bauen(speicher, schluessel, qtbot)

    monkeypatch.setattr("ui.hauptfenster.SuchDialog", lambda parent: _FakeSuchDialog("Wann war ich im Urlaub?"))
    fenster._suchen_oeffnen()

    assert fenster._suche.ki_antwort.isHidden() is False
    qtbot.waitUntil(lambda: fenster._frage_task is None, timeout=2000)
    assert fenster._suche.ki_antwort.toPlainText() == "Die Antwort auf die Frage."


def test_frage_waehrend_laufender_frage_zeigt_fehler(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "Text")
    speicher.stichpunkte_speichern(schluessel, EintragTyp.TAG, "2026-09-20", "- Punkt", "hash")
    fenster = _bauen(speicher, schluessel, qtbot)

    fenster._frage_stellen("Erste Frage?")
    assert fenster._frage_task is not None

    fehler = []
    monkeypatch.setattr("ui.hauptfenster.show_error", lambda parent, text: fehler.append(text))
    fenster._frage_stellen("Zweite Frage?")

    assert fehler == ["Es wird noch eine vorherige Frage beantwortet. Bitte kurz warten."]
    qtbot.waitUntil(lambda: fenster._frage_task is None, timeout=2000)


def test_zusammenfassung_neu_erstellen_fragt_bei_manuell_bearbeitet(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.MONAT, "2026-08", "Von Hand geschrieben")
    speicher.manuell_bearbeitet_setzen(EintragTyp.MONAT, "2026-08", True)
    fenster = _bauen(speicher, schluessel, qtbot)

    gefragt = []
    monkeypatch.setattr("ui.hauptfenster.confirm", lambda *a, **k: (gefragt.append(a), False)[1])
    fenster._zusammenfassung_neu_erstellen(EintragTyp.MONAT, "2026-08")

    assert len(gefragt) == 1
    unveraendert = speicher.eintrag_laden(schluessel, EintragTyp.MONAT, "2026-08")
    assert unveraendert.text == "Von Hand geschrieben"


def test_zusammenfassung_neu_erstellen_ohne_rueckfrage_bei_tag(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, "2026-08-05", "Text")
    fenster = _bauen(speicher, schluessel, qtbot)

    fenster._zusammenfassung_neu_erstellen(EintragTyp.TAG, "2026-08-05")
    qtbot.waitUntil(
        lambda: speicher.eintrag_laden(schluessel, EintragTyp.TAG, "2026-08-05").stichpunkte != "",
        timeout=2000,
    )
    fenster._ki_worker.abbrechen_und_warten()


def test_datumswechsel_ohne_aenderung_tut_nichts(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    fenster._datumswechsel_pruefen()  # gleiches Datum wie beim Start -> kein Effekt
    assert fenster._letztes_datum == date.today()


def test_datumswechsel_ueber_monatsgrenze_prueft_faellige_uebersichten(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)

    aufrufe = []
    monkeypatch.setattr(fenster, "_ki_hintergrund_pruefen", lambda: aufrufe.append(True))
    fenster._letztes_datum = date(2026, 8, 31)
    fenster._datumswechsel_pruefen()

    assert fenster._letztes_datum == date.today()
    assert aufrufe == [True]


def test_datumswechsel_innerhalb_des_monats_prueft_nicht_erneut(qtbot, speicher, monkeypatch):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)

    aufrufe = []
    monkeypatch.setattr(fenster, "_ki_hintergrund_pruefen", lambda: aufrufe.append(True))
    heute = date.today()
    fenster._letztes_datum = date.fromordinal(heute.toordinal() - 1)
    fenster._datumswechsel_pruefen()

    assert fenster._letztes_datum == heute
    assert aufrufe == []


def test_close_event_ohne_laufende_tasks(qtbot, speicher):
    schluessel = speicher.einrichten("passwort")
    fenster = _bauen(speicher, schluessel, qtbot)
    fenster.close()  # darf nicht abstuerzen, auch ohne laufende Hintergrund-Tasks


def test_close_waehrend_laufender_zusammenfassung_wartet_statt_abzubrechen(qtbot, speicher):
    """Regressionstest: Schließen kurz nach dem Speichern darf eine noch laufende
    Zusammenfassung nicht abwürgen (siehe ki/ollama_client.WARTE_TIMEOUT_MS)."""
    import time

    class LangsamerFakeClient:
        def json_anfrage(self, **kwargs):
            time.sleep(0.3)  # simuliert ein Modell, das noch lädt/antwortet
            return {"stichpunkte": ["Ein Punkt"]}

    schluessel = speicher.einrichten("passwort")
    heute = date.today().isoformat()
    speicher.eintrag_speichern(schluessel, EintragTyp.TAG, heute, "Ein ereignisreicher Tag.")
    fenster = _bauen(speicher, schluessel, qtbot)
    fenster._ollama_client = LangsamerFakeClient()

    fenster._ki_worker.hinzufuegen(fenster._tages_auftrag(heute))
    assert fenster._ki_worker.laeuft_gerade() is True

    fenster.close()  # blockiert bis zu WARTE_TIMEOUT_MS, statt den Task mitten drin zu killen
    qtbot.waitUntil(
        lambda: speicher.eintrag_laden(schluessel, EintragTyp.TAG, heute).stichpunkte != "", timeout=2000
    )
