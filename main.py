"""Startdatei des Tagebuchs (Abschnitt 10 des Konzepts)."""
from __future__ import annotations

import logging
import sys
from datetime import date

from PySide6.QtWidgets import QApplication, QDialog

from kern.config import APP_NAME, Config, app_dir
from kern.speicher import Speicher
from ui.anmelde_dialog import AnmeldeDialog
from ui.einrichtung_dialog import EinrichtungDialog
from ui.hauptfenster import HauptFenster


def _anmelden_oder_einrichten(speicher: Speicher) -> bytes | None:
    dialog = EinrichtungDialog(speicher) if not speicher.ist_eingerichtet() else AnmeldeDialog(speicher)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.schluessel
    return None


def main() -> int:
    logs = app_dir() / "logs"
    logs.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=logs / "app.log",
        level=logging.INFO,
        encoding="utf-8",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    config = Config.load()

    while True:
        speicher = Speicher(config.datenbank_pfad())
        schluessel = _anmelden_oder_einrichten(speicher)
        if schluessel is None:
            speicher.close()
            return 0

        speicher.last_run_date_setzen(date.today().isoformat())

        fenster = HauptFenster(config, speicher, schluessel)
        fenster.showMaximized()
        fenster.initial_focus()
        code = app.exec()

        if not fenster.account_geloescht:
            return code
        # Der Account wurde gelöscht: von vorn beginnen (Ersteinrichtung).


if __name__ == "__main__":
    sys.exit(main())
