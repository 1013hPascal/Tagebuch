"""Hauptfenster: Menüleiste, Statuszeile, Umschalten zwischen den Ansichten (Abschnitt 7 des Konzepts)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget

from kern import datum, zeitplan
from kern.config import Config
from kern.modelle import EintragTyp
from kern.speicher import Speicher
from ki import fragen, zusammenfasser
from ki.ollama_client import WARTE_TIMEOUT_MS, OllamaClient, OllamaFehler
from ki.server import OllamaServer
from ki.warteschlange import Auftrag

from .announcer import announce, announcer
from .common import confirm, show_error
from .editor_ansicht import EditorAnsicht
from .ki_worker import KiWarteschlangenVerarbeiter
from .lese_ansicht import LeseAnsicht
from .menus import AccessibleMenu
from .passwort_dialog import AccountLoeschenDialog, PasswortAendernDialog
from .such_dialog import SuchDialog
from .such_ergebnis_ansicht import SuchErgebnisAnsicht
from .uebersicht_ansicht import UebersichtAnsicht
from .workers import AufgabenFehler, Task

_RUECKSCHAU_EINTRAEGE = [
    (EintragTyp.TAG, "Tagesübersicht", "Ctrl+1"),
    (EintragTyp.MONAT, "Monatsübersicht", "Ctrl+2"),
    (EintragTyp.JAHR, "Jahresübersicht", "Ctrl+3"),
]


class HauptFenster(QMainWindow):
    def __init__(self, config: Config, speicher: Speicher, schluessel: bytes) -> None:
        super().__init__()
        self.config = config
        self.speicher = speicher
        self.schluessel = schluessel
        self.account_geloescht = False
        self._aktueller_typ = EintragTyp.TAG
        self._letzte_auswahl: str | None = None
        self._ki_in_bearbeitung: tuple[EintragTyp, str] | None = None
        self._frage_task: Task | None = None
        self._server_start_task: Task | None = None
        self._wird_beendet = False

        self.setWindowTitle("Tagebuch")
        announcer.target = self

        self._ollama_client = OllamaClient(config.ollama_host)
        self._ollama_server = OllamaServer(config.ollama_host)
        self._ki_worker = KiWarteschlangenVerarbeiter(self)
        self._ki_worker.status_geaendert.connect(self._status_setzen)
        self._ki_worker.auftrag_gestartet.connect(self._ki_auftrag_gestartet)
        self._ki_worker.auftrag_fertig.connect(self._ki_auftrag_fertig)
        self._ki_worker.nicht_erreichbar.connect(self._ki_nicht_erreichbar)

        self._uebersicht = UebersichtAnsicht(
            speicher, self._schluessel_holen, ist_in_bearbeitung=self._ist_in_bearbeitung
        )
        self._editor = EditorAnsicht(speicher, self._schluessel_holen, config)
        self._lese = LeseAnsicht()
        self._suche = SuchErgebnisAnsicht()

        self._uebersicht.eintrag_oeffnen_editor.connect(self._editor_oeffnen)
        self._uebersicht.eintrag_oeffnen_leseansicht.connect(self._leseansicht_oeffnen)
        self._uebersicht.zusammenfassung_neu_erstellen_angefordert.connect(self._zusammenfassung_neu_erstellen)
        self._editor.gespeichert.connect(self._nach_speichern)
        self._editor.abgebrochen.connect(self._zurueck_zur_uebersicht)
        self._editor.status_geaendert.connect(self._status_setzen)
        self._lese.zurueck.connect(self._zurueck_zur_uebersicht)
        self._lese.bearbeiten_angefordert.connect(self._bearbeiten_von_leseansicht)
        self._suche.eintrag_oeffnen_editor.connect(self._editor_oeffnen)
        self._suche.eintrag_oeffnen_leseansicht.connect(self._leseansicht_oeffnen)
        self._suche.zurueck.connect(self._zurueck_zur_uebersicht)

        self._stapel = QStackedWidget()
        self._stapel.addWidget(self._uebersicht)
        self._stapel.addWidget(self._editor)
        self._stapel.addWidget(self._lese)
        self._stapel.addWidget(self._suche)
        self.setCentralWidget(self._stapel)

        self._status_label = QLabel("Bereit")
        self._status_label.setAccessibleName("Status")
        self._status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.statusBar().addWidget(self._status_label)

        self._menue_aufbauen()
        self._uebersicht.anzeigen(self._aktueller_typ)
        QTimer.singleShot(0, self._ollama_server_starten)

        self._letztes_datum = date.today()
        self._datumswechsel_timer = QTimer(self)
        self._datumswechsel_timer.setInterval(60_000)
        self._datumswechsel_timer.timeout.connect(self._datumswechsel_pruefen)
        self._datumswechsel_timer.start()

    def initial_focus(self) -> None:
        self._uebersicht.fokus_liste()

    def _schluessel_holen(self) -> bytes:
        return self.schluessel

    def _status_setzen(self, text: str) -> None:
        self._status_label.setText(text)

    def _ist_in_bearbeitung(self, typ: EintragTyp, zeitraum: str) -> bool:
        return self._ki_in_bearbeitung == (typ, zeitraum)

    # ------------------------------------------------------------------
    # KI-Zusammenfassungen (Abschnitt 9)
    # ------------------------------------------------------------------

    def _tages_auftrag(self, zeitraum: str) -> Auftrag:
        beschreibung = f"Erstelle Stichpunkte für {datum.tag_anzeigen(zeitraum)} …"

        def ausfuehren() -> None:
            zusammenfasser.tages_stichpunkte_erzeugen(
                self.speicher,
                self.schluessel,
                zeitraum,
                client=self._ollama_client,
                modell=self.config.ollama_modell,
            )

        return Auftrag(EintragTyp.TAG, zeitraum, beschreibung, ausfuehren)

    def _monats_auftrag(self, zeitraum: str) -> Auftrag:
        beschreibung = f"Erstelle Monatsübersicht {datum.monat_anzeigen(zeitraum)} …"

        def ausfuehren() -> None:
            zusammenfasser.monats_uebersicht_erzeugen(
                self.speicher,
                self.schluessel,
                zeitraum,
                client=self._ollama_client,
                modell=self.config.ollama_modell,
                num_ctx=self.config.ollama_num_ctx,
            )

        return Auftrag(EintragTyp.MONAT, zeitraum, beschreibung, ausfuehren)

    def _jahres_auftrag(self, zeitraum: str) -> Auftrag:
        beschreibung = f"Erstelle Jahresübersicht {datum.jahr_anzeigen(zeitraum)} …"

        def ausfuehren() -> None:
            zusammenfasser.jahres_uebersicht_erzeugen(
                self.speicher,
                self.schluessel,
                zeitraum,
                client=self._ollama_client,
                modell=self.config.ollama_modell,
                num_ctx=self.config.ollama_num_ctx,
            )

        return Auftrag(EintragTyp.JAHR, zeitraum, beschreibung, ausfuehren)

    def _ollama_server_starten(self) -> None:
        """Startet Ollama als Unterprozess, sobald das Passwort stimmt (dieses Fenster also
        entsteht) - läuft schon ein Server (z. B. über die Tray-App), wird der einfach
        mitbenutzt. Läuft im Hintergrund, damit ein langsamer oder fehlender Ollama-Start die
        Oberfläche nicht blockiert."""

        def arbeit(_task: Task) -> None:
            self._ollama_server.start()

        task = Task(arbeit, self)
        task.result.connect(self._ollama_server_bereit)
        task.error.connect(self._ollama_server_bereit)
        task.cancelled.connect(self._ollama_server_abgebrochen)
        task.finished.connect(task.deleteLater)
        self._server_start_task = task
        task.start()

    def _ollama_server_bereit(self, *_args) -> None:
        self._server_start_task = None
        self._ki_hintergrund_pruefen()

    def _ollama_server_abgebrochen(self) -> None:
        # Passiert nur beim Beenden des Programms, siehe closeEvent.
        self._server_start_task = None

    def _ki_hintergrund_pruefen(self) -> None:
        heute = date.today()
        for zeitraum in zusammenfasser.veraltete_tage_finden(self.speicher, self.schluessel):
            self._ki_worker.hinzufuegen(self._tages_auftrag(zeitraum))
        for zeitraum in zeitplan.faellige_monate(self.speicher, self.schluessel, heute):
            self._ki_worker.hinzufuegen(self._monats_auftrag(zeitraum))
        for zeitraum in zeitplan.faellige_jahre(self.speicher, self.schluessel, heute):
            self._ki_worker.hinzufuegen(self._jahres_auftrag(zeitraum))

    def _datumswechsel_pruefen(self) -> None:
        heute = date.today()
        if heute == self._letztes_datum:
            return
        voriges_datum = self._letztes_datum
        self._letztes_datum = heute

        if self._stapel.currentWidget() is self._uebersicht:
            self._uebersicht.anzeigen(self._aktueller_typ)

        monats_oder_jahreswechsel = (voriges_datum.year, voriges_datum.month) != (heute.year, heute.month)
        if monats_oder_jahreswechsel:
            self._ki_hintergrund_pruefen()

    def _zusammenfassung_neu_erstellen(self, typ: EintragTyp, zeitraum: str) -> None:
        if typ != EintragTyp.TAG:
            vorhandener = self.speicher.eintrag_laden(self.schluessel, typ, zeitraum)
            if vorhandener is not None and vorhandener.manuell_bearbeitet:
                if not confirm(
                    self,
                    "Zusammenfassung neu erstellen",
                    "Deine Änderungen an dieser Übersicht gehen dabei verloren. Fortfahren?",
                ):
                    return

        auftrag_erstellen = {
            EintragTyp.TAG: self._tages_auftrag,
            EintragTyp.MONAT: self._monats_auftrag,
            EintragTyp.JAHR: self._jahres_auftrag,
        }[typ]
        self._ki_worker.hinzufuegen(auftrag_erstellen(zeitraum))

    def _ki_auftrag_gestartet(self, typ: EintragTyp, zeitraum: str) -> None:
        self._ki_in_bearbeitung = (typ, zeitraum)
        self._uebersicht.aktualisiere_vorschau()

    def _ki_auftrag_fertig(self, typ: EintragTyp, zeitraum: str) -> None:
        self._ki_in_bearbeitung = None
        wird_gerade_angezeigt = (
            self._stapel.currentWidget() is self._uebersicht
            and self._aktueller_typ == typ
            and self._uebersicht.aktuelle_auswahl() == zeitraum
        )
        self._uebersicht.aktualisiere_vorschau()
        self._status_label.setText("Bereit")
        if wird_gerade_angezeigt:
            # Nur ansagen, wenn der Nutzer diesen Eintrag gerade betrachtet (Abschnitt 11) -
            # sonst würde das Nachholen vieler alter Tage beim Start die Ansage zuspammen.
            announce("Zusammenfassung fertig.")

    def _ki_nicht_erreichbar(self) -> None:
        text = "Die KI ist gerade nicht erreichbar. Zusammenfassungen werden später erstellt."
        self._status_label.setText(text)
        announce(text)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt-Signatur)
        """Wartet auf laufende Hintergrund-Threads, bevor das Fenster wirklich schließt.

        Ein QThread darf nicht zerstört werden, während er noch läuft (z. B. eine
        Spracherkennung oder eine Ollama-Anfrage) - das stürzt den Prozess ab. Läuft nur
        einmal: ein zweites Schließen (z. B. wenn etwas den Vorgang wiederholt) darf nicht
        erneut auf möglicherweise inzwischen zerstörte Task-Objekte zugreifen.
        """
        if not self._wird_beendet:
            self._wird_beendet = True
            if self._ki_worker.laeuft_gerade() or self._frage_task is not None:
                # Nur ansagen, wenn wirklich etwas wartet - sonst schließt das Fenster wie
                # gewohnt sofort, ohne unnötige Meldung.
                self._status_setzen("Wird noch fertiggestellt, bitte kurz warten …")
                announce("Wird noch fertiggestellt, bitte kurz warten …", dringend=True)
            self._editor.hintergrund_abbrechen_und_warten()
            self._ki_worker.abbrechen_und_warten()
            if self._frage_task is not None:
                self._frage_task.cancel()
                self._frage_task.wait(WARTE_TIMEOUT_MS)
            if self._server_start_task is not None:
                self._server_start_task.cancel()
                self._server_start_task.wait(WARTE_TIMEOUT_MS)
            self._ollama_server.stop()  # tut nichts, falls wir den Server nicht selbst gestartet haben
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Menü
    # ------------------------------------------------------------------

    def _menue_aufbauen(self) -> None:
        datei = AccessibleMenu("&Datei", self)
        self.menuBar().addMenu(datei)

        aktion_suchen = datei.addAction("Suche/Frage")
        aktion_suchen.setShortcut("Ctrl+F")
        aktion_suchen.triggered.connect(self._suchen_oeffnen)

        aktion_passwort = datei.addAction("Passwort ändern")
        aktion_passwort.triggered.connect(self._passwort_aendern)

        datei.addAction("Account löschen").triggered.connect(self._account_loeschen)

        datei.addSeparator()
        aktion_beenden = datei.addAction("Beenden")
        aktion_beenden.setShortcut("Ctrl+Q")
        aktion_beenden.triggered.connect(self.close)

        rueckschau = AccessibleMenu("&Rückschau", self)
        self.menuBar().addMenu(rueckschau)
        gruppe = QActionGroup(self)
        gruppe.setExclusive(True)
        self._rueckschau_aktionen = {}
        for typ, text, kuerzel in _RUECKSCHAU_EINTRAEGE:
            aktion = rueckschau.addAction(text)
            aktion.setCheckable(True)
            aktion.setShortcut(kuerzel)
            aktion.triggered.connect(lambda _checked, t=typ: self._rueckschau_wechseln(t))
            gruppe.addAction(aktion)
            self._rueckschau_aktionen[typ] = aktion
        self._rueckschau_aktionen[EintragTyp.TAG].setChecked(True)

    def _rueckschau_wechseln(self, typ: EintragTyp) -> None:
        self._aktueller_typ = typ
        self._uebersicht.anzeigen(typ)
        self._stapel.setCurrentWidget(self._uebersicht)
        self._uebersicht.fokus_liste()

    # ------------------------------------------------------------------
    # Ansichten wechseln
    # ------------------------------------------------------------------

    def _editor_oeffnen(self, typ: EintragTyp, eintrag, mit_spracheingabe: bool) -> None:
        if self._stapel.currentWidget() is self._uebersicht:
            self._letzte_auswahl = self._uebersicht.aktuelle_auswahl()
        self._editor.oeffnen(typ, eintrag, mit_spracheingabe=mit_spracheingabe, heute=date.today())
        self._stapel.setCurrentWidget(self._editor)
        self._editor.fokus_text_feld()

    def _leseansicht_oeffnen(self, typ: EintragTyp, zeitraum: str) -> None:
        self._letzte_auswahl = self._uebersicht.aktuelle_auswahl()
        eintrag = self.speicher.eintrag_laden(self.schluessel, typ, zeitraum)
        self._lese.anzeigen(typ, zeitraum, eintrag.text if eintrag is not None else "")
        self._stapel.setCurrentWidget(self._lese)
        self._lese.fokus_text()

    def _bearbeiten_von_leseansicht(self, typ: EintragTyp, zeitraum: str) -> None:
        eintrag = self.speicher.eintrag_laden(self.schluessel, typ, zeitraum)
        # Spracheingabe ist auch beim Bearbeiten vergangener Tage verfügbar (Abschnitt 14,
        # Annahme A2), aber nicht bei Monats-/Jahresübersichten - die entstehen normalerweise
        # per KI, manuelles Bearbeiten dient dort nur der Korrektur des vorhandenen Textes.
        self._editor_oeffnen(typ, eintrag, typ == EintragTyp.TAG)

    def _nach_speichern(self, typ: EintragTyp, zeitraum: str) -> None:
        self._aktueller_typ = typ
        self._rueckschau_aktionen[typ].setChecked(True)
        self._uebersicht.anzeigen(typ)
        self._uebersicht.auswaehlen(zeitraum)
        self._stapel.setCurrentWidget(self._uebersicht)
        self._uebersicht.fokus_liste()
        self._status_label.setText("Gespeichert")
        announce("Gespeichert.")
        if typ == EintragTyp.TAG:
            self._ki_worker.hinzufuegen(self._tages_auftrag(zeitraum))

    def _zurueck_zur_uebersicht(self) -> None:
        self._uebersicht.anzeigen(self._aktueller_typ)
        if self._letzte_auswahl is not None:
            self._uebersicht.auswaehlen(self._letzte_auswahl)
        self._stapel.setCurrentWidget(self._uebersicht)
        self._uebersicht.fokus_liste()

    # ------------------------------------------------------------------
    # Datei-Menü
    # ------------------------------------------------------------------

    def _suchen_oeffnen(self) -> None:
        dialog = SuchDialog(self)
        if dialog.exec():
            treffer = self.speicher.suchen(self.schluessel, dialog.suchbegriff)
            self._suche.anzeigen(dialog.suchbegriff, treffer)
            self._stapel.setCurrentWidget(self._suche)
            self._suche.fokus_liste()
            if "?" in dialog.suchbegriff:
                self._frage_stellen(dialog.suchbegriff)

    def _frage_stellen(self, frage: str) -> None:
        """Beantwortet eine Frage zur Vergangenheit im Hintergrund (Abschnitt 7.6).

        Läuft, wie die Spracheingabe und die KI-Warteschlange, in einem eigenen Task, damit
        die Oberfläche währenddessen bedienbar bleibt. Eine bereits laufende Frage blockiert
        eine neue - die Ollama-Anfrage lässt sich nicht mitten im Warten unterbrechen, ohne die
        Oberfläche einzufrieren (`Task.wait()` würde blockieren, bis die laufende Anfrage von
        selbst fertig ist).
        """
        if self._frage_task is not None:
            show_error(self, "Es wird noch eine vorherige Frage beantwortet. Bitte kurz warten.")
            return

        self._suche.frage_beantwortung_starten()

        speicher = self.speicher
        schluessel = self.schluessel
        client = self._ollama_client
        modell = self.config.ollama_modell
        num_ctx = self.config.ollama_num_ctx

        def arbeit(_task: Task) -> str:
            try:
                return fragen.frage_beantworten(
                    speicher, schluessel, frage, client=client, modell=modell, num_ctx=num_ctx
                )
            except OllamaFehler as exc:
                raise AufgabenFehler(str(exc)) from exc

        task = Task(arbeit, self)
        task.result.connect(self._frage_beantwortet)
        task.error.connect(self._frage_fehlgeschlagen)
        task.cancelled.connect(self._frage_abgebrochen)
        task.finished.connect(task.deleteLater)
        self._frage_task = task
        task.start()

    def _frage_beantwortet(self, antwort: str) -> None:
        self._frage_task = None
        self._suche.frage_beantwortet(antwort)

    def _frage_fehlgeschlagen(self, fehlertext: str) -> None:
        self._frage_task = None
        self._suche.frage_fehlgeschlagen(fehlertext)

    def _frage_abgebrochen(self) -> None:
        # Passiert nur beim Beenden des Programms, siehe closeEvent.
        self._frage_task = None

    def _passwort_aendern(self) -> None:
        dialog = PasswortAendernDialog(self.speicher, self)
        if dialog.exec():
            self.schluessel = dialog.neuer_schluessel
            self._status_label.setText("Passwort geändert.")
            announce("Passwort geändert.")

    def _account_loeschen(self) -> None:
        dialog = AccountLoeschenDialog(self.speicher, self)
        if dialog.exec():
            self.account_geloescht = True
            QApplication.instance().quit()
