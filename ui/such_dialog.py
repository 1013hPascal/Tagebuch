"""Such-Dialog (Abschnitt 7.6 des Konzepts)."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from .common import name_widget, show_error


class SuchDialog(QDialog):
    """Ein Feld für beides: ein Suchbegriff (Volltextsuche) oder eine Frage zur Vergangenheit
    (z. B. „Wann war ich zuletzt in Berlin?“) - enthält das Eingegebene ein Fragezeichen,
    beantwortet die KI die Frage zusätzlich anhand der vorhandenen Zusammenfassungen
    (Abschnitt 7.6)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.suchbegriff: str = ""

        self.setWindowTitle("Suche/Frage")
        self.setModal(True)

        label = QLabel("Suchbegriff oder Frage")
        self.suchbegriff_feld = QLineEdit()
        label.setBuddy(self.suchbegriff_feld)
        name_widget(self.suchbegriff_feld, "Suchbegriff oder Frage")

        hinweis = QLabel(
            "Ein Suchbegriff durchsucht die Einträge. Bei einer Frage mit Fragezeichen "
            "sucht zusätzlich die KI nach einer Antwort."
        )
        hinweis.setWordWrap(True)

        knoepfe = QDialogButtonBox()
        knopf_suchen = knoepfe.addButton("Suchen", QDialogButtonBox.ButtonRole.AcceptRole)
        knopf_suchen.setDefault(True)
        knoepfe.addButton(QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self._suchen)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(self.suchbegriff_feld)
        layout.addWidget(hinweis)
        layout.addWidget(knoepfe)

        self.suchbegriff_feld.setFocus()

    def _suchen(self) -> None:
        text = self.suchbegriff_feld.text().strip()
        if not text:
            show_error(self, "Bitte einen Suchbegriff oder eine Frage eingeben.")
            self.suchbegriff_feld.setFocus()
            return
        self.suchbegriff = text
        self.accept()
