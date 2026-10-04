"""Gemeinsame UI-Hilfsfunktionen (Muster aus dem Chatbot-Projekt übernommen)."""
from __future__ import annotations

from enum import Enum

from PySide6.QtWidgets import QMessageBox, QPlainTextEdit, QWidget

# Qt fügt beim Einfügen mehrzeiligen Texts oft den Unicode-Zeilentrenner U+2028 ein.
# Der bleibt für Screenreader/Braillezeile unsichtbar als "neue Zeile" - deshalb wird
# er beim Einfügen durch einen echten Zeilenumbruch ersetzt.
_UNSICHTBARER_ZEILENTRENNER = chr(0x2028)


def name_widget(widget: QWidget, name: str) -> None:
    """Setzt nur den Accessible Name, bewusst keine Accessible Description.

    Eine Beschreibung würde die Braillezeile mit Name, Rolle und Beschreibung
    überladen; Tastenkürzel gehören ins Menü, nicht in jedes Feld.
    """
    widget.setAccessibleName(name)


class JaNeinAbbrechen(Enum):
    JA = "ja"
    NEIN = "nein"
    ABBRECHEN = "abbrechen"


def confirm(parent: QWidget, titel: str, text: str, *, default_yes: bool = False) -> bool:
    """Ja/Nein-Rückfrage. Standardmäßig ist 'Nein' der Standardknopf (die sicherere Wahl)."""
    box = QMessageBox(parent)
    box.setWindowTitle(titel)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    ja = box.addButton("Ja", QMessageBox.ButtonRole.YesRole)
    nein = box.addButton("Nein", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(ja if default_yes else nein)
    box.setEscapeButton(nein)
    box.exec()
    return box.clickedButton() is ja


def confirm_ja_abbrechen(parent: QWidget, titel: str, text: str) -> bool:
    """Rückfrage mit 'Ja' und 'Abbrechen' (statt 'Ja'/'Nein'), z. B. beim Anhängen an einen
    vorhandenen Eintrag. Standardknopf und Escape sind 'Abbrechen' (die sicherere Wahl)."""
    box = QMessageBox(parent)
    box.setWindowTitle(titel)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    ja = box.addButton("Ja", QMessageBox.ButtonRole.YesRole)
    abbrechen = box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(abbrechen)
    box.setEscapeButton(abbrechen)
    box.exec()
    return box.clickedButton() is ja


def frage_ja_nein_abbrechen(parent: QWidget, titel: str, text: str) -> JaNeinAbbrechen:
    """Dreiwege-Rückfrage (z. B. 'Änderungen speichern?'). Standardknopf und Escape sind 'Abbrechen'."""
    box = QMessageBox(parent)
    box.setWindowTitle(titel)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    ja = box.addButton("Ja", QMessageBox.ButtonRole.YesRole)
    nein = box.addButton("Nein", QMessageBox.ButtonRole.NoRole)
    abbrechen = box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(abbrechen)
    box.setEscapeButton(abbrechen)
    box.exec()
    geklickt = box.clickedButton()
    if geklickt is ja:
        return JaNeinAbbrechen.JA
    if geklickt is nein:
        return JaNeinAbbrechen.NEIN
    return JaNeinAbbrechen.ABBRECHEN


def show_error(parent: QWidget, text: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("Fehler")
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Warning)
    box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def show_info(parent: QWidget, text: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle("Hinweis")
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Information)
    box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


class PlainEdit(QPlainTextEdit):
    """Mehrzeiliges Textfeld: Tab wechselt den Fokus statt ein Tabzeichen einzufügen.

    Die Eingabetaste selbst wird bewusst NICHT überschrieben - QPlainTextEdit erzeugt
    dabei bereits von sich aus einen echten Absatzumbruch, der über `toPlainText()`
    zuverlässig als "\\n" erscheint (anders als bei QTextEdit gibt es hier keinen
    unsichtbaren weichen Zeilenumbruch). Ein eigener Override hatte hier unerwünschte
    Nebenwirkungen auf die Pfeiltasten-Navigation. Nur eingefügter Text (Zwischenablage)
    wird normalisiert, siehe `insertFromMimeData`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabChangesFocus(True)

    def insertFromMimeData(self, source) -> None:  # noqa: N802 (Qt-Signatur)
        if source.hasText():
            self.textCursor().insertText(source.text().replace(_UNSICHTBARER_ZEILENTRENNER, "\n"))
        else:
            super().insertFromMimeData(source)
