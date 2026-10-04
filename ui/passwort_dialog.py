"""Dialoge zum Ändern des Passworts und zum Löschen des Accounts (Abschnitt 5 des Konzepts)."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from kern.krypto import FalschesPasswort
from kern.speicher import Speicher

from .common import name_widget, show_error


def _passwort_feld(beschriftung: str) -> tuple[QLabel, QLineEdit]:
    label = QLabel(beschriftung)
    feld = QLineEdit()
    feld.setEchoMode(QLineEdit.EchoMode.Password)
    label.setBuddy(feld)
    name_widget(feld, beschriftung)
    return label, feld


class PasswortAendernDialog(QDialog):
    """Altes Passwort prüfen, neues Passwort zweimal eingeben, alle Einträge neu verschlüsseln."""

    def __init__(self, speicher: Speicher, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.speicher = speicher
        self.neuer_schluessel: bytes | None = None

        self.setWindowTitle("Passwort ändern")
        self.setModal(True)

        label_alt, self.altes_passwort = _passwort_feld("Altes Passwort")
        label_neu, self.neues_passwort = _passwort_feld("Neues Passwort")
        label_wdh, self.wiederholung = _passwort_feld("Neues Passwort wiederholen")

        knoepfe = QDialogButtonBox()
        knopf_aendern = knoepfe.addButton("Ändern", QDialogButtonBox.ButtonRole.AcceptRole)
        knopf_aendern.setDefault(True)
        knoepfe.addButton(QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self._aendern)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        for label, feld in (
            (label_alt, self.altes_passwort),
            (label_neu, self.neues_passwort),
            (label_wdh, self.wiederholung),
        ):
            layout.addWidget(label)
            layout.addWidget(feld)
        layout.addWidget(knoepfe)

        self.altes_passwort.setFocus()

    def _aendern(self) -> None:
        try:
            schluessel_alt = self.speicher.anmelden(self.altes_passwort.text())
        except FalschesPasswort:
            show_error(self, "Das alte Passwort ist nicht richtig.")
            self.altes_passwort.clear()
            self.altes_passwort.setFocus()
            return

        neu = self.neues_passwort.text()
        if not neu:
            show_error(self, "Bitte ein neues Passwort eingeben.")
            self.neues_passwort.setFocus()
            return
        if neu != self.wiederholung.text():
            show_error(self, "Die Passwörter stimmen nicht überein.")
            self.neues_passwort.clear()
            self.wiederholung.clear()
            self.neues_passwort.setFocus()
            return

        self.neuer_schluessel = self.speicher.passwort_aendern(schluessel_alt, neu)
        self.accept()


class AccountLoeschenDialog(QDialog):
    """Löscht den gesamten Account unwiderruflich, nach Bestätigung durch das Passwort."""

    def __init__(self, speicher: Speicher, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.speicher = speicher

        self.setWindowTitle("Account löschen")
        self.setModal(True)

        warnung = QLabel(
            "Es werden alle Tagebucheinträge unwiderruflich gelöscht. "
            "Das kann nicht rückgängig gemacht werden."
        )
        warnung.setWordWrap(True)

        label_passwort, self.passwort = _passwort_feld("Passwort")

        knoepfe = QDialogButtonBox()
        knopf_loeschen = knoepfe.addButton("Löschen", QDialogButtonBox.ButtonRole.AcceptRole)
        knopf_abbrechen = knoepfe.addButton(QDialogButtonBox.StandardButton.Cancel)
        knopf_abbrechen.setDefault(True)
        knoepfe.accepted.connect(self._loeschen)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(warnung)
        layout.addWidget(label_passwort)
        layout.addWidget(self.passwort)
        layout.addWidget(knoepfe)

        self.passwort.setFocus()

    def _loeschen(self) -> None:
        try:
            self.speicher.anmelden(self.passwort.text())
        except FalschesPasswort:
            show_error(self, "Das Passwort ist nicht richtig.")
            self.passwort.clear()
            self.passwort.setFocus()
            return
        self.speicher.account_loeschen()
        self.accept()
