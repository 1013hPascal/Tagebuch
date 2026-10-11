# Tagebuch

Ein verschlüsseltes Sprach-Tagebuch für Windows: Einträge per Tastatur oder Sprache
schreiben, lokal mit AES-GCM verschlüsselt speichern, und automatisch mit einem lokalen
Sprachmodell (Ollama) zu Tages-Stichpunkten, Monats- und Jahresübersichten
zusammenfassen lassen. Läuft vollständig lokal, ohne Internet (bis auf das einmalige
Herunterladen des Spracherkennungsmodells) und ist vollständig per Tastatur und
Screenreader (z. B. NVDA) bedienbar.

Das vollständige Konzept steht in [`KONZEPT_Tagebuch.md`](KONZEPT_Tagebuch.md).

## Voraussetzungen

- **Windows 10/11**
- **Python 3.11 oder neuer** (getestet mit 3.14) - [python.org](https://www.python.org/downloads/windows/), beim Setup „Add python.exe to PATH“ ankreuzen
- **[Ollama](https://ollama.com/download/windows)** installiert und mindestens ein Modell heruntergeladen, z. B.:
  ```powershell
  ollama pull gemma4:12b
  ```
  Ollama muss dafür **nicht** dauerhaft im Hintergrund laufen: Das Tagebuch startet es beim
  Anmelden selbst als Unterprozess (falls es nicht schon läuft) und beendet es beim Schließen
  wieder - genau wie beim Chatbot-Projekt. Läuft schon ein Ollama-Server (z. B. über die
  Tray-App), wird der einfach mitbenutzt.
  Ist Ollama gar nicht installiert, funktioniert das Tagebuch trotzdem vollständig (Schreiben,
  Lesen, Suchen, Spracheingabe) - nur die automatischen Zusammenfassungen und Fragen zur
  Vergangenheit (Abschnitt „Suche/Frage“) bleiben dann aus.
- Ein Mikrofon, falls die Spracheingabe genutzt werden soll (optional - Tippen geht immer)

## Installation

1. Projektordner öffnen (PowerShell):
   ```powershell
   cd Pfad\zum\Tagebuch
   ```
2. Abhängigkeiten installieren:
   ```powershell
   pip install -r requirements.txt
   ```
   Das lädt unter anderem PySide6, `cryptography`, `faster-whisper`, `sounddevice` und
   `numpy`. `faster-whisper` selbst lädt beim ersten Gebrauch der Spracheingabe einmalig
   das Spracherkennungsmodell aus dem Internet herunter (Standard `small`, ca. 500 MB) und
   speichert es lokal - danach funktioniert alles offline.

   **Hinweis für Rechner mit aktivem Windows Smart App Control:** `faster-whisper`
   installiert das Paket `av` (PyAV) mit, obwohl das Tagebuch es nie braucht (Audio kommt
   immer live vom Mikrofon, nie aus einer Datei). Smart App Control blockiert die
   mitgelieferte native `av`-Datei unter Umständen als „nicht vertrauenswürdig“, wodurch
   `faster-whisper` sich nicht importieren lässt. Siehe die Kommentare in
   [`requirements.txt`](requirements.txt) für den Workaround (ein leerer Ersatz für das
   `av`-Paket, da seine echte Funktionalität ohnehin nie aufgerufen wird).

3. Programm starten:
   ```powershell
   python main.py
   ```
   Oder per Doppelklick auf [`tagebuch.bat`](tagebuch.bat) im Projektordner - startet ohne
   zusätzliches Konsolenfenster. Für eine Verknüpfung auf dem Desktop oder im Startmenü:
   Rechtsklick auf `tagebuch.bat` → Senden an → Desktop (Verknüpfung erstellen).
4. Beim allerersten Start ein Passwort festlegen. **Wichtig: Dieses Passwort lässt sich
   nicht zurücksetzen.** Geht es verloren, sind alle Einträge unwiderruflich unlesbar.

## Konfiguration

Alle Einstellungen stehen in [`config.toml`](config.toml) im Projektordner:

| Einstellung | Bedeutung |
|---|---|
| `db_pfad` | Pfad zur Datenbankdatei. Leer = `%APPDATA%\Tagebuch\tagebuch.db` |
| `ollama_host` | Adresse des Ollama-Servers |
| `ollama_modell` | Modellname für Zusammenfassungen, z. B. `gemma4:12b` |
| `ollama_num_ctx` | Kontextfenster für Ollama-Anfragen (Jahresübersichten können lang werden) |
| `whisper_modell` | `small` (Standard), `medium` oder `large-v3-turbo` (genauer, aber langsamer) |
| `whisper_sprache` | Sprachcode für die Spracherkennung, Standard `de` |
| `max_aufnahme_sekunden` | Maximale Aufnahmedauer, danach wird automatisch beendet |

Änderungen werden erst beim nächsten Start wirksam.

Die verschlüsselte Datenbank liegt standardmäßig unter `%APPDATA%\Tagebuch\`, Logs unter
`%APPDATA%\Tagebuch\logs\app.log` (enthalten nie Klartext aus den Einträgen).

## Bedienung

Vollständig per Tastatur:

- **Strg+1 / 2 / 3**: Tages-/Monats-/Jahresübersicht
- **Strg+F**: Suche/Frage (ein „?“ im Feld lässt zusätzlich die KI antworten)
- **Strg+S**: im Editor speichern
- **Escape**: zurück zur Übersicht bzw. Dialog schließen
- **Entf** oder Kontextmenü-Taste/Umschalt+F10 auf einem Eintrag: löschen oder
  Zusammenfassung neu erstellen
- **Strg+Q**: Beenden

Ausführlich beschrieben in Abschnitt 7 des Konzepts. Für Screenreader-Nutzung siehe
[`ACCESSIBILITY_TESTS.md`](ACCESSIBILITY_TESTS.md).

## Tests

```powershell
python -m pytest
```

154 automatisierte Tests (keine echte Ollama- oder Mikrofon-Verbindung nötig - alle
externen Abhängigkeiten sind für Tests austauschbar).

## Datenschutz

- Tagebuchtexte, Stichpunkte und Übersichten werden ausschließlich verschlüsselt
  gespeichert (Scrypt zur Schlüsselableitung, AES-GCM pro Feld).
- Sprachaufnahmen werden nie auf die Festplatte geschrieben, nur im Arbeitsspeicher
  gehalten, bis der Text erkannt ist.
- Der Schlüssel existiert nur im Arbeitsspeicher, solange das Programm läuft.
- Es werden keine Daten an einen Server im Internet gesendet (Ollama und Whisper laufen
  lokal).

## Änderungen

### 1.0.1 (11.10.2026)

- Release-Notizen und Versionierung aktualisiert

### 1.0.0 (04.10.2026)

- Exe-Einrichtung mit KI
- Exe-Einstellungen
- Erste Version
