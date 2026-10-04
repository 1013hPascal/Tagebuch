"""Dialog zur Ersteinrichtung: neues Passwort festlegen (Abschnitt 5 des Konzepts)."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from kern.speicher import Speicher

from .common import name_widget, show_error


class EinrichtungDialog(QDialog):
    """Fragt beim ersten Start ein neues Passwort ab (zweimal, zur Sicherheit) und legt den Account an."""

    def __init__(self, speicher: Speicher, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.speicher = speicher
        self.schluessel: bytes | None = None

        self.setWindowTitle("Tagebuch einrichten")
        self.setModal(True)

        hinweis = QLabel(
            "Wenn das Passwort verloren geht, sind die Einträge nicht wiederherstellbar."
        )
        hinweis.setWordWrap(True)

        label_passwort = QLabel("Passwort")
        self.passwort = QLineEdit()
        self.passwort.setEchoMode(QLineEdit.EchoMode.Password)
        label_passwort.setBuddy(self.passwort)
        name_widget(self.passwort, "Passwort")

        label_wiederholung = QLabel("Passwort wiederholen")
        self.wiederholung = QLineEdit()
        self.wiederholung.setEchoMode(QLineEdit.EchoMode.Password)
        label_wiederholung.setBuddy(self.wiederholung)
        name_widget(self.wiederholung, "Passwort wiederholen")

        knoepfe = QDialogButtonBox()
        knopf_einrichten = knoepfe.addButton("Einrichten", QDialogButtonBox.ButtonRole.AcceptRole)
        knopf_einrichten.setDefault(True)
        knoepfe.addButton(QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self._einrichten)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(label_passwort)
        layout.addWidget(self.passwort)
        layout.addWidget(label_wiederholung)
        layout.addWidget(self.wiederholung)
        layout.addWidget(knoepfe)

        self.passwort.setFocus()

    def _einrichten(self) -> None:
        passwort = self.passwort.text()
        if not passwort:
            show_error(self, "Bitte ein Passwort eingeben.")
            self.passwort.setFocus()
            return
        if passwort != self.wiederholung.text():
            show_error(self, "Die Passwörter stimmen nicht überein.")
            self.passwort.clear()
            self.wiederholung.clear()
            self.passwort.setFocus()
            return
        self.schluessel = self.speicher.einrichten(passwort)
        self.accept()
