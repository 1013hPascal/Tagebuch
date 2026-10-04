"""Anmeldedialog: Passwort abfragen, um das Tagebuch zu öffnen (Abschnitt 5 des Konzepts)."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from kern.krypto import FalschesPasswort
from kern.speicher import Speicher

from .common import name_widget, show_error


class AnmeldeDialog(QDialog):
    """Fragt das Passwort ab und leitet daraus den Schlüssel ab."""

    def __init__(self, speicher: Speicher, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.speicher = speicher
        self.schluessel: bytes | None = None

        self.setWindowTitle("Tagebuch öffnen")
        self.setModal(True)

        label = QLabel("Passwort")
        self.passwort = QLineEdit()
        self.passwort.setEchoMode(QLineEdit.EchoMode.Password)
        label.setBuddy(self.passwort)
        name_widget(self.passwort, "Passwort")

        knoepfe = QDialogButtonBox()
        knopf_oeffnen = knoepfe.addButton("Öffnen", QDialogButtonBox.ButtonRole.AcceptRole)
        knopf_oeffnen.setDefault(True)
        knoepfe.addButton(QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self._anmelden)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(self.passwort)
        layout.addWidget(knoepfe)

        self.passwort.setFocus()

    def _anmelden(self) -> None:
        try:
            self.schluessel = self.speicher.anmelden(self.passwort.text())
        except FalschesPasswort:
            show_error(self, "Das Passwort ist nicht richtig.")
            self.passwort.clear()
            self.passwort.setFocus()
            return
        self.accept()
