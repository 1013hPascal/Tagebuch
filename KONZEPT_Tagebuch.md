# Konzept: Verschlüsseltes Sprach-Tagebuch mit lokaler KI (PySide6)

Dieses Dokument beschreibt vollständig, was gebaut werden soll. Es richtet sich an Claude Code als Arbeitsgrundlage. Bei Unklarheiten gilt: erst nachfragen, nicht raten. Abschnitt 14 listet Annahmen, die bewusst getroffen wurden und die der Nutzer ändern kann.

---

## 1. Ziel

Eine Windows-Desktop-Anwendung in Python mit PySide6, in der man täglich Tagebucheinträge per Tastatur oder Sprache verfasst. Alles läuft lokal, ohne Server und ohne Cloud:

- Einträge werden verschlüsselt in einer lokalen SQLite-Datei gespeichert.
- Spracheingabe wird lokal mit Whisper (faster-whisper) in Text umgewandelt.
- Ein lokales Sprachmodell über Ollama erstellt pro Tag drei Stichpunkte, pro Monat eine Monatsübersicht und pro Jahr eine Jahresübersicht.
- Die Bedienung ist vollständig per Tastatur möglich und mit Screenreader gut nutzbar. Das hat hohe Priorität.

## 2. Wichtigste Vorgabe: Aufbau vom Chatbot-Projekt übernehmen

Der Nutzer stellt sein bestehendes Chatbot-Projekt (PySide6, lokale KI über Ollama) zur Verfügung. **Bevor irgendetwas programmiert wird**, analysiert Claude Code dieses Projekt und übernimmt daraus:

- den Aufbau (Ordnerstruktur, Aufteilung in Module, Startdatei)
- die Art der Bedienung (Tastaturführung, Fokuslogik, Umgang mit Listen, Kontextmenüs, Statusmeldungen)
- die Umsetzung der Barrierefreiheit (Accessible Names, Labels, Ansagen)
- die Anbindung an Ollama (Client, Konfiguration, Fehlerbehandlung)
- Hintergrundverarbeitung (Threads bzw. Worker, damit die Oberfläche nie einfriert)
- Einstellungen und Konfigurationsdatei
- Code-Stil, Benennungen, Logging

Ergebnis dieses ersten Schritts: eine kurze schriftliche Zusammenfassung an den Nutzer, was übernommen wird und wo das neue Projekt davon abweicht. Erst nach Bestätigung beginnt die Umsetzung.

Wo dieses Konzept und das Chatbot-Projekt sich widersprechen, gilt dieses Konzept für die Funktionen und das Chatbot-Projekt für die technische Umsetzung. Im Zweifel nachfragen.

## 3. Zielsystem

- Lenovo ThinkPad E14 Gen 7, Intel Core Ultra 7 258V (8 Kerne), Intel Arc 140V, 32 GB RAM
- Windows 11 Pro
- Ollama ist installiert und nutzt die GPU über Vulkan (etwa 18 GiB gemeinsamer Speicher)
- Kein CUDA. Whisper läuft daher auf der CPU (faster-whisper mit int8).
- Das Programm muss ohne Internet funktionieren. Einzige Ausnahme: das einmalige Herunterladen des Whisper-Modells beim ersten Start.

## 4. Technik

- Python 3.11 oder neuer, PySide6
- `cryptography` für Verschlüsselung (Scrypt zur Schlüsselableitung, AES-GCM zur Verschlüsselung)
- `faster-whisper` für Spracherkennung, Sprache fest auf Deutsch (`language="de"`)
- `sounddevice` und `numpy` für die Mikrofonaufnahme
- Ollama-Anbindung so wie im Chatbot-Projekt
- SQLite (Standardbibliothek `sqlite3`)
- `pytest` für Tests

Das Sprachmodell für Zusammenfassungen wird in der Konfigurationsdatei festgelegt. Claude Code prüft mit `ollama list`, welche Modelle installiert sind, und trägt als Standard das installierte Gemma-Modell mit etwa 12B ein.

Das Whisper-Modell ist ebenfalls konfigurierbar. Standard: `small`. Alternativen: `medium` oder `large-v3-turbo` (genauer, aber langsamer).

## 5. Datenschutz und Verschlüsselung

### Grundsätze

- Tagebuchtexte, Stichpunkte, Monats- und Jahresübersichten werden **nur verschlüsselt** gespeichert.
- Sprachaufnahmen werden **nie** gespeichert. Sie existieren nur im Arbeitsspeicher, bis die Umwandlung in Text fertig ist.
- Klartext wird nie in Logdateien geschrieben, auch nicht in Fehlermeldungen.
- Der Schlüssel existiert nur im Arbeitsspeicher, solange das Programm läuft.

### Umsetzung

- Aus dem Passwort wird mit Scrypt ein 256-Bit-Schlüssel abgeleitet. Das Salt (zufällig, 16 Byte) und die Scrypt-Parameter stehen in der Tabelle `meta`.
- Jedes verschlüsselte Feld wird mit AES-GCM und einer eigenen zufälligen Nonce (12 Byte) verschlüsselt. Gespeichert wird Nonce plus Chiffrat.
- Zur Passwortprüfung wird beim Einrichten ein fester Prüftext verschlüsselt und in `meta` abgelegt. Lässt er sich beim Anmelden entschlüsseln, ist das Passwort richtig.
- Die Datumsangaben der Einträge bleiben unverschlüsselt, damit sortiert werden kann. Das heißt: Wer die Datei hat, sieht, an welchen Tagen es Einträge gibt, aber nicht deren Inhalt.

### Erster Start

Dialog „Tagebuch einrichten“ mit zwei Passwortfeldern („Passwort“ und „Passwort wiederholen“) und dem deutlichen Hinweis: **Wenn das Passwort verloren geht, sind die Einträge nicht wiederherstellbar.**

### Anmeldung

Dialog mit einem Passwortfeld und dem Knopf „Öffnen“. Bei falschem Passwort eine klare Meldung, Fokus zurück ins Passwortfeld, Feld geleert.

### Passwort ändern

Menü Datei, Eintrag „Passwort ändern“: altes Passwort, neues Passwort, Wiederholung. Danach werden alle Einträge in einer einzigen Datenbank-Transaktion neu verschlüsselt. Bricht etwas ab, bleibt der alte Zustand erhalten.

### Account löschen

Da das Passwort nicht zurückgesetzt werden kann, muss es sich zuverlässig einprägen lassen. Deshalb: Beim Einrichten wird das Passwort zweimal eingegeben (Abschnitt „Erster Start“); stimmen beide Felder nicht überein, klare Meldung „Die Passwörter stimmen nicht überein.“, beide Felder werden geleert, Fokus zurück ins erste Feld.

Menü Datei, Eintrag „Account löschen“ (nur vorhanden, weil man zum Programmstart ohnehin angemeldet sein muss — der Eintrag ist also immer erreichbar, sobald das Hauptfenster offen ist). Öffnet einen Dialog:

- Warnhinweis: „Es werden alle Tagebucheinträge unwiderruflich gelöscht. Das kann nicht rückgängig gemacht werden.“
- Eingabefeld „Passwort“ (zur Bestätigung, dass wirklich die berechtigte Person handelt)
- Knöpfe „Löschen“ und „Abbrechen“ (Standardknopf, Escape schließt ebenfalls mit Abbrechen)

Ablauf beim Klick auf „Löschen“:
1. Eingegebenes Passwort gegen den `verifier` prüfen. Falsch: Meldung „Das Passwort ist nicht richtig.“, Feld geleert, Fokus bleibt im Dialog.
2. Richtig: Datenbankdatei vollständig löschen (alle Einträge, `meta`-Tabelle, Schlüssel).
3. Zurück zum Einrichtungsdialog (Abschnitt „Erster Start“), als wäre das Programm zum ersten Mal gestartet worden. Keine Anwendung wird beendet.

## 6. Datenmodell (SQLite)

Datei: `tagebuch.db` im Benutzerdatenordner (z. B. `%APPDATA%\Tagebuch\`), Pfad konfigurierbar.

### Tabelle `meta`

| Spalte | Inhalt |
|---|---|
| key | Text, Primärschlüssel |
| value | Blob oder Text |

Einträge: `schema_version`, `kdf_salt`, `kdf_params`, `verifier`, `last_run_date`.

### Tabelle `eintraege`

| Spalte | Inhalt |
|---|---|
| id | Integer, Primärschlüssel |
| typ | `tag`, `monat` oder `jahr` |
| zeitraum | Text: `JJJJ-MM-TT`, `JJJJ-MM` oder `JJJJ` |
| text_enc | verschlüsselter Haupttext |
| stichpunkte_enc | verschlüsselte Stichpunkte für die Vorschau (kann leer sein) |
| stichpunkte_quelle_hash | Hash des Textes, aus dem die Stichpunkte erzeugt wurden |
| manuell_bearbeitet | 0 oder 1 (nur für Monat und Jahr relevant) |
| erstellt_am | Zeitstempel |
| geaendert_am | Zeitstempel |

Eindeutigkeit: `UNIQUE(typ, zeitraum)`. Pro Tag, Monat und Jahr gibt es also genau einen Eintrag.

Der Hash (SHA-256 über den Klartext, gespeichert als Hex) dient dazu, zu erkennen, ob Stichpunkte veraltet sind. Er wird nur berechnet, wenn der Text ohnehin entschlüsselt vorliegt.

Hinweis: Streng genommen verrät der Hash, ob sich zwei Texte gleichen. Wenn das stört, stattdessen einen HMAC mit einem aus dem Schlüssel abgeleiteten Teilschlüssel verwenden. Empfehlung: HMAC.

## 7. Aufbau der Oberfläche

Ein Hauptfenster mit Menüleiste, Statusleiste und einem `QStackedWidget` für die Ansichten:

1. **Übersicht** (Liste plus Vorschau)
2. **Editor** (Schreiben, mit oder ohne Spracheingabe)
3. **Leseansicht** (Text lesen, Knopf „Bearbeiten“)
4. **Suchergebnisse** (gleiche Darstellung wie die Übersicht)

Die Übersicht gibt es in drei Varianten: Tage, Monate, Jahre. **Alle drei sehen gleich aus und verhalten sich gleich.** Umgeschaltet wird über das Menü „Rückschau“.

### 7.1 Menüleiste

**Datei**
- Suchen (Strg+F)
- Passwort ändern
- Account löschen
- Beenden (Strg+Q)

**Rückschau** (die drei Einträge sind wählbar, der aktive ist als ausgewählt markiert)
- Tagesübersicht (Strg+1)
- Monatsübersicht (Strg+2)
- Jahresübersicht (Strg+3)

Nach dem Umschalten landet der Fokus auf dem ersten Eintrag der Liste.

### 7.2 Übersicht

Beim Programmstart (nach der Anmeldung) erscheint die **Tagesübersicht**, Fokus auf dem obersten Listeneintrag.

Aufbau: links bzw. oben die Liste, daneben bzw. darunter der Vorschaubereich.

**Listeneinträge in der Tagesübersicht:**

1. Ganz oben immer: **„Was ich zu erzählen habe“**
2. Darunter alle Tageseinträge, **neuester oben, ältester unten**
   - Beschriftung: Wochentag und Datum, z. B. „Dienstag, 22.09.2026“
   - Der heutige Eintrag zusätzlich mit „(heute)“

**Listeneinträge in der Monats- und Jahresübersicht:** gleicher Aufbau. Oben ein Eintrag zum Neuanlegen (siehe Abschnitt 14, Annahme A1), darunter die Einträge, neuester oben.
- Monat: z. B. „September 2026“
- Jahr: z. B. „2025“

**Vorschau:** Wird ein Listeneintrag ausgewählt (Pfeiltasten), zeigt der Vorschaubereich dessen Stichpunkte. Mit **Tab** springt der Fokus von der Liste in die Vorschau, mit **Umschalt+Tab** zurück.
- Die Vorschau ist ein mehrzeiliges, schreibgeschütztes Textfeld mit Accessible Name „Vorschau“.
- Gibt es noch keine Stichpunkte: „Noch keine Zusammenfassung vorhanden.“
- Wird gerade eine erzeugt: „Zusammenfassung wird erstellt …“
- Beim obersten Eintrag „Was ich zu erzählen habe“ zeigt die Vorschau einen kurzen Hinweis, z. B. „Neuen Eintrag für heute schreiben.“

**Aktivieren eines Eintrags** (Enter oder Doppelklick):
- „Was ich zu erzählen habe“: öffnet den **Editor mit Spracheingabe** für heute. Gibt es für heute schon einen Eintrag, wird dieser geöffnet, damit man weiterschreibt.
- Eintrag des **heutigen Tages**: öffnet ebenfalls den **Editor mit Spracheingabe** mit dem bisherigen Text.
- Eintrag eines **vergangenen Tages**: öffnet die **Leseansicht**.
- Monats- oder Jahreseintrag: öffnet die **Leseansicht**.

Ein einfacher Klick wählt nur aus und aktualisiert die Vorschau.

**Kontextmenü** auf einem Listeneintrag (rechte Maustaste, Kontextmenü-Taste oder Umschalt+F10):
- **Eintrag löschen** (auch mit der Taste Entf erreichbar)
  - Sicherheitsabfrage: „Eintrag vom 22.09.2026 wirklich löschen? Das kann nicht rückgängig gemacht werden.“ Standardknopf ist **Nein**.
  - Danach Fokus auf den nächsten Eintrag in der Liste.
- **Zusammenfassung neu erstellen** (Vorschlag, siehe Abschnitt 14, Annahme A5)
- Beim obersten Eintrag „Was ich zu erzählen habe“ gibt es kein Kontextmenü.

### 7.3 Editor mit Spracheingabe (heutiger Tag und neue Einträge)

Wird geöffnet über „Was ich zu erzählen habe“ oder den Eintrag des heutigen Tages.

**Elemente in Tab-Reihenfolge:**

1. **Datum**: einzeiliges Eingabefeld, Beschriftung „Datum“, vorbelegt mit dem heutigen Datum im Format `TT.MM.JJJJ`
2. **Was geschah**: mehrzeiliges Textfeld. Beschriftung und Accessible Name lauten „Was geschah“, nicht „Textfeld“.
3. **Ich muss dir was erzählen**: Knopf für die Spracheingabe
4. **Speichern**: Knopf

**Fokus beim Öffnen:** im Feld „Was geschah“, Cursor am Ende des Textes. Von dort erreicht man mit Umschalt+Tab das Datum und mit Tab die Spracheingabe, mit einem weiteren Tab den Knopf Speichern.

Wichtig für die Tastaturbedienung: In den mehrzeiligen Textfeldern muss Tab den Fokus weitergeben statt ein Tabzeichen einzufügen (`setTabChangesFocus(True)`). Enter erzeugt im Textfeld einen Zeilenumbruch.

**Spracheingabe („Ich muss dir was erzählen“):**
- Erster Druck: Aufnahme startet. Der Knopf heißt jetzt „Aufnahme beenden“. Ansage bzw. Statusmeldung: „Aufnahme läuft“.
- Zweiter Druck: Aufnahme endet. Der Knopf heißt währenddessen „Wird umgewandelt …“, bleibt aber fokussierbar (der Fokus bleibt auf dem Knopf) - ein deaktiviertes Widget würde in Qt automatisch den Fokus verlieren. Weitere Klicks werden während der Umwandlung ignoriert. Statusmeldung/Ansage: „Bearbeitung läuft.“
- Ergebnis: Der erkannte Text wird **unten an den vorhandenen Text angehängt**, getrennt durch einen Zeilenumbruch (bzw. Leerzeile, wenn schon Text da ist). Vorhandener Text wird nie überschrieben.
- Danach heißt der Knopf wieder „Ich muss dir was erzählen“. Der **Fokus springt ins Textfeld „Was geschah“**, und zwar genau an die Stelle, an der der neue Text eingefügt wurde (nicht ans Ende danach) - so lässt sich das Ergebnis direkt weiterlesen oder korrigieren. Statusmeldung/Ansage: „Fertig transkribiert.“
- Wurde nichts erkannt: „Es wurde nichts verstanden.“, Fokus bleibt auf dem Spracheingabe-Knopf.
- Kein Mikrofon oder Fehler: verständliche Meldung, das Schreiben per Tastatur bleibt jederzeit möglich.
- Das Whisper-Modell wird beim ersten Gebrauch im Hintergrund geladen und danach im Speicher gehalten.
- Maximale Aufnahmedauer: konfigurierbar, Standard 10 Minuten, danach automatisch beenden.

**Speichern:**
- Datum prüfen (siehe Abschnitt 8). Bei Fehler: Meldung, Fokus ins Datumsfeld.
- Leerer Text wird nicht gespeichert (Meldung „Es gibt noch nichts zu speichern.“).
- Gibt es für das eingegebene Datum schon einen **anderen** Eintrag, Rückfrage: „Für diesen Tag gibt es schon einen Eintrag. Text dort anhängen?“ mit Ja und Abbrechen.
- Nach dem Speichern: zurück zur Übersicht, Fokus auf dem gespeicherten Eintrag, Statusmeldung „Gespeichert“.
- Danach werden die Stichpunkte im Hintergrund neu erzeugt (Abschnitt 9.1).
- Tastenkürzel zusätzlich: Strg+S. Der Speichern-Knopf ist außerdem mit Enter bedienbar, sobald er fokussiert ist (`setDefault(True)`); ebenso löst Enter im Datumsfeld das Speichern aus. Im mehrzeiligen Feld „Was geschah“ erzeugt Enter dagegen weiterhin nur einen Zeilenumbruch.

**Verlassen ohne Speichern:** Escape führt zurück zur Übersicht. Gibt es ungespeicherte Änderungen, Rückfrage „Änderungen speichern?“ mit Ja, Nein und Abbrechen.

### 7.4 Leseansicht (vergangene Tage, Monate, Jahre)

**Elemente in Tab-Reihenfolge:**

1. Mehrzeilige, **schreibgeschützte** Textausgabe mit dem vollständigen Text. Accessible Name: das Datum bzw. der Zeitraum, z. B. „Eintrag vom 21.09.2026“, „September 2026“, „Jahr 2025“.
2. **Bearbeiten**: Knopf, auch mit Enter bedienbar, sobald er fokussiert ist (`setDefault(True)`)

Fokus beim Öffnen: in der Textausgabe, am Anfang, damit man mit den Pfeiltasten lesen kann. Escape führt zurück zur Übersicht, Fokus auf dem zuvor gewählten Eintrag.

### 7.5 Editor ohne Spracheingabe (Bearbeiten)

Wird über „Bearbeiten“ in der Leseansicht geöffnet.

**Elemente in Tab-Reihenfolge:**

1. **Datum** (bei Monaten „Monat“, bei Jahren „Jahr“), vorbelegt mit dem Zeitraum des Eintrags
2. **Was geschah**: mehrzeiliges Textfeld mit dem vorhandenen Text
3. **Ich muss dir was erzählen**: Knopf für die Spracheingabe, aber **nur bei Tageseinträgen** - bei Monats-/Jahresübersichten bleibt er ausgeblendet und aus der Tab-Reihenfolge ausgenommen, da diese normalerweise per KI entstehen und manuelles Bearbeiten hier nur der Korrektur dient (Abschnitt 14, Annahme A2)
4. **Speichern**

Fokus beim Öffnen: im Textfeld. Bei Tageseinträgen (mit Spracheingabe) Cursor am Ende, sonst am Anfang - dieselbe Regel wie in Abschnitt 7.3. Spracheingabe, Speichern, Prüfen und Rückfragen wie in Abschnitt 7.3. Wird das Datum auf einen Zeitraum geändert, für den es schon einen Eintrag gibt: Rückfrage „Dort gibt es schon einen Eintrag. Text anhängen?“.

Beim Speichern einer Monats- oder Jahresübersicht wird `manuell_bearbeitet = 1` gesetzt (Abschnitt 9.4).

### 7.6 Suche/Frage

- Öffnen über Datei, „Suche/Frage“ oder Strg+F.
- Ein kleiner Dialog mit dem Eingabefeld „Suchbegriff oder Frage“, einem Hinweistext und dem Knopf „Suchen“. Dasselbe Feld deckt zwei Fälle ab:
  1. **Suchbegriff** (kein Fragezeichen): reine Volltextsuche wie bisher.
  2. **Frage** (enthält ein „?“, z. B. „Wann war ich zuletzt in Berlin?“): zusätzlich zur Volltextsuche beantwortet die KI die Frage anhand der vorhandenen Zusammenfassungen.
- **Volltextsuche:** Da alles verschlüsselt ist, erfolgt sie im Arbeitsspeicher: Alle Einträge werden entschlüsselt und durchsucht. Bei einem Tagebuch ist das schnell genug. Gesucht wird ohne Beachtung von Groß- und Kleinschreibung in Text und Stichpunkten, über Tage, Monate und Jahre.
- Ergebnisse erscheinen als Liste in derselben Darstellung wie die Übersicht, neueste oben. Beschriftung wie gewohnt, bei Monat und Jahr mit Kennzeichnung, z. B. „Monatsübersicht September 2026“.
- Oberster Eintrag: „Suchergebnisse für „Urlaub“: 7 Treffer“ (nicht aktivierbar). Bei null Treffern: „Keine Treffer für …“.
- Tab führt in die Vorschau. Die Vorschau zeigt hier zusätzlich einen kurzen Textausschnitt rund um die Fundstelle.
- Enter öffnet den Eintrag nach denselben Regeln wie in der Übersicht.
- Escape führt zurück zur zuletzt aktiven Übersicht.

**KI-Antwort auf eine Frage** (nur bei „?“ im Eingabefeld, `ki/fragen.py`):
- Läuft, wie die Spracheingabe und die KI-Warteschlange, in einem eigenen Hintergrund-Task, damit die Oberfläche bedienbar bleibt.
- Als Kontext dienen dieselben Zusammenfassungen wie in der Rückschau: alle Jahres- und Monatsübersichten sowie die Tages-Stichpunkte der Tage, die noch zu keiner Monatsübersicht gehören (z. B. der laufende Monat). So bleibt der Kontext auch nach Jahren kompakt, und es muss nicht erneut der volle Rohtext verarbeitet werden.
- Über dem Suchergebnis erscheint ein eigenes, schreibgeschütztes Feld „KI-Antwort“ (zunächst unsichtbar). Statusmeldung/Ansage „Antwort wird gesucht …“, danach die Antwort mit Ansage „Antwort gefunden.“ und Fokus im Antwortfeld. Gibt es noch keine Zusammenfassungen, antwortet die App direkt „Dazu gibt es noch keine Einträge oder Zusammenfassungen.“, ohne die KI zu bemühen.
- Ist Ollama nicht erreichbar oder liefert eine unbrauchbare Antwort, erscheint die Fehlermeldung im selben Feld.
- Läuft schon eine Frage im Hintergrund, blockiert eine zweite mit der Meldung „Es wird noch eine vorherige Frage beantwortet. Bitte kurz warten.“ (eine laufende Ollama-Anfrage lässt sich nicht unterbrechen, ohne die Oberfläche einzufrieren).

## 8. Datumsfeld und Prüfung

| Ansicht | Format | Beispiel |
|---|---|---|
| Tag | `TT.MM.JJJJ` | 22.09.2026 |
| Monat | `MM.JJJJ` | 09.2026 |
| Jahr | `JJJJ` | 2025 |

Prüfung beim Speichern:

- Das Format muss stimmen. Führende Nullen sollen optional sein (`2.9.2026` ist erlaubt).
- Das Datum muss existieren (kein 31.02.).
- Das Datum darf nicht in der Zukunft liegen.
- Fehlermeldung konkret, z. B. „Das Datum 31.02.2026 gibt es nicht. Bitte im Format TT.MM.JJJJ eingeben.“ Fokus danach ins Datumsfeld.

## 9. KI-Zusammenfassungen

Alle Aufrufe laufen im Hintergrund in einer Warteschlange nacheinander ab, damit die Oberfläche bedienbar bleibt und der Laptop nicht überlastet wird. Die Statusleiste zeigt, was gerade passiert, z. B. „Erstelle Monatsübersicht August 2026 …“.

Die Modellausgabe wird als strukturiertes JSON angefordert (Ollama-Option `format` mit JSON-Schema) und vor dem Speichern geprüft. Ist die Ausgabe unbrauchbar, wird es einmal wiederholt, danach bleibt der Eintrag ohne Zusammenfassung und wird beim nächsten Start erneut versucht.

Alle Prompts stehen in einer eigenen Datei (`ki/prompts.py`), damit der Nutzer sie leicht anpassen kann. Grundregeln in allen Prompts: auf Deutsch antworten, nur Informationen aus dem Text verwenden, nichts erfinden, keine Bewertungen oder Ratschläge.

### 9.1 Tages-Stichpunkte

- Eingabe: der Text eines Tages
- Ausgabe: genau drei Stichpunkte zu den wichtigsten Ereignissen des Tages, jeweils kurz. Hat der Tag weniger Inhalt, entsprechend weniger.
- Wann: nach jedem Speichern eines Tageseintrags, sowie beim Programmstart für alle Tage, deren Stichpunkte fehlen oder veraltet sind (Hash stimmt nicht mehr).

### 9.2 Monatsübersicht

- Eingabe: die Stichpunkte aller Tage des Monats, jeweils mit Datum (nicht die vollständigen Texte, damit es in den Kontext des Modells passt)
- Ausgabe:
  - `text`: eine **ausführliche** Monatsübersicht in mehreren zusammenhängenden Absätzen. Erzählt, was die großen Ereignisse und Unternehmungen des Monats waren, und geht auch auf die Stimmung ein: gab es Erfolge oder schöne Momente, gab es Rückschläge oder schwierige Phasen, was hat einen im Monat beschäftigt. Nur, soweit sich das aus den Tages-Stichpunkten erkennen lässt.
  - `stichpunkte`: drei bis fünf Stichpunkte für die Vorschau (bleiben kurz, unabhängig von der Länge von `text`)
- Wann: **beim ersten Programmstart in einem neuen Monat** für den vergangenen Monat. Wurde das Programm mehrere Monate nicht gestartet, werden alle fehlenden Monate nachgeholt, ältester zuerst.
- Monate ohne einen einzigen Tageseintrag bekommen keine Übersicht.
- Vorher müssen die Tages-Stichpunkte des Monats vollständig sein (Reihenfolge in der Warteschlange: erst Tage, dann Monate, dann Jahre).
- Ein Monat, der einmal eine Übersicht bekommen hat, wird **nicht** automatisch neu erzeugt, auch wenn später Tageseinträge dieses Monats geändert werden (Annahme A7). Nur „Zusammenfassung neu erstellen“ erzeugt sie neu.

### 9.3 Jahresübersicht

- Eingabe: die zwölf (bzw. vorhandenen) Monatsübersichten des Jahres
- Ausgabe wie beim Monat, aber **deutlich ausführlicher**:
  - `text`: mehrere Absätze. Was waren die großen Ereignisse, Ausflüge und Erlebnisse, die das Jahr geprägt haben. Ausführlich auch zur persönlichen Entwicklung: Höhen und Tiefen, Freude und Trauer, was gut gelaufen ist und was weniger, welche Learnings erkennbar sind. Nur, soweit sich das aus den Monatsübersichten ergibt – nichts hinzuerfinden, keine eigenen Bewertungen der KI, nur wiedergeben, was in den Monatsübersichten an Ereignissen und Stimmungen bereits steht.
  - `stichpunkte`: drei bis fünf Stichpunkte für die Vorschau
- Wann: **beim ersten Programmstart im neuen Jahr** (also am 1. Januar oder am ersten späteren Tag, an dem das Programm gestartet wird) für das vergangene Jahr. Vorher wird die Dezember-Übersicht erzeugt. Fehlende Jahre werden nachgeholt.
- Ein Jahr, das einmal eine Übersicht bekommen hat, wird ebenfalls nicht automatisch neu erzeugt (wie beim Monat).

### 9.4 Manuell bearbeitete Übersichten

Eine Monats- oder Jahresübersicht mit `manuell_bearbeitet = 1` wird **nie automatisch überschrieben**. Nur über „Zusammenfassung neu erstellen“ im Kontextmenü, mit Rückfrage: „Deine Änderungen an dieser Übersicht gehen dabei verloren. Fortfahren?“.

### 9.5 Wenn Ollama nicht läuft

- Das Tagebuch funktioniert trotzdem vollständig. Schreiben, Lesen, Suchen und Spracheingabe hängen nicht von Ollama ab.
- Einmalige Statusmeldung: „Die KI ist gerade nicht erreichbar. Zusammenfassungen werden später erstellt.“
- Beim nächsten Start wird automatisch nachgeholt.

**Wichtig beim Beenden (Fund vom 23.09.2026):** Ein frisch gestartetes großes Modell wie gemma4:12b muss erst von der Platte geladen werden - das kann deutlich länger als ein paar Sekunden dauern, gerade beim allerersten Aufruf nach dem automatischen Ollama-Start (Abschnitt 9.6). Schließt man das Tagebuch, während eine Zusammenfassung noch läuft, **wartet** das Programm deshalb bis zu `ki/ollama_client.WARTE_TIMEOUT_MS` (etwas mehr als die Anfrage selbst erlaubt, siehe `ANFRAGE_TIMEOUT_S`), statt den Hintergrund-Thread mitten in der Ausführung abzuwürgen. Ein fehlender Tageseintrag wird zwar dank des Hash-Vergleichs (`veraltete_tage_finden`) beim nächsten Start ohnehin automatisch nachgeholt - aber ohne dieses Warten würde jedes Mal das bereits geladene Modell verworfen und beim nächsten Start das langsame Laden von vorn beginnen, statt die gerade laufende Anfrage einfach zu Ende zu bringen. Läuft dabei wirklich etwas, zeigt die Statuszeile „Wird noch fertiggestellt, bitte kurz warten …“, damit das Fenster nicht einfach unerklärlich hängen bleibt.

### 9.6 Ollama startet automatisch mit dem Tagebuch (`ki/server.py`)

Wie im Chatbot-Projekt (`core/engine.py`) muss Ollama nicht dauerhaft laufen (z. B. über die Tray-App), sondern nur während das Tagebuch geöffnet ist:

- Sobald das Passwort stimmt (also sobald `HauptFenster` entsteht), wird im Hintergrund geprüft, ob Ollama bereits erreichbar ist (`GET /api/version`). Wenn nicht, wird `ollama serve` als Unterprozess gestartet und kurz gewartet, bis es antwortet (Protokoll unter `%APPDATA%\Tagebuch\logs\ollama.log`).
- Läuft schon ein Ollama-Server (von Hand gestartet oder über die Tray-App), wird der einfach mitbenutzt und beim Beenden **nicht** angetastet.
- Ist Ollama nicht installiert oder startet es nicht rechtzeitig, bleibt es bei Abschnitt 9.5: Das Tagebuch funktioniert weiter, nur ohne KI-Zusammenfassungen.
- Erst danach wird geprüft, was an Zusammenfassungen fehlt (Startablauf, Abschnitt 10) - so sind, sobald Ollama bereit ist, gleich alle fälligen Zusammenfassungen dran, ohne dass man das Tagebuch dafür neu starten muss.
- Wurde der Server vom Tagebuch selbst gestartet, wird er beim Beenden des Programms wieder angehalten (inklusive des Modell-Runner-Kindprozesses, sonst bliebe der verwaist im Speicher).

## 10. Datumswechsel und Programmstart

**Startablauf:**

1. Konfiguration laden
2. Erster Start: Einrichtungsdialog. Sonst: Anmeldung.
3. Datenbank öffnen, Schema prüfen, bei Bedarf migrieren
4. Tagesübersicht anzeigen, Fokus auf „Was ich zu erzählen habe“
4a. Im Hintergrund: Ollama starten, falls nötig (Abschnitt 9.6), danach die Warteschlange füllen (Schritt 5)
5. Im Hintergrund prüfen, was an Zusammenfassungen fehlt (Tage, dann Monate, dann Jahr), und die Warteschlange füllen
6. `last_run_date` in `meta` aktualisieren

**Datumswechsel bei laufendem Programm:** Ein Timer prüft jede Minute, ob sich das Datum geändert hat. Wenn ja:
- Die Liste wird aktualisiert. Der gestrige Eintrag gilt ab jetzt als vergangener Tag.
- Bei Monats- oder Jahreswechsel werden die fälligen Übersichten in die Warteschlange gestellt.
- Ein gerade geöffneter Editor wird **nicht** geschlossen. Das Datumsfeld behält sein Datum, sodass der Text beim Speichern dem richtigen (gestrigen) Tag zugeordnet wird.

## 11. Barrierefreiheit

Die Anwendung wird mit Screenreader (z. B. NVDA) bedient. Deshalb gilt verbindlich:

- Jedes Bedienelement hat einen sinnvollen Accessible Name. Textfelder bekommen sichtbare Beschriftungen, die per `setBuddy` verknüpft sind.
- Tab-Reihenfolgen sind ausdrücklich festgelegt (`setTabOrder`), genau wie in Abschnitt 7 beschrieben.
- Mehrzeilige Felder: Tab wechselt den Fokus.
- Statusänderungen (Aufnahme läuft, Bearbeitung läuft, Fertig transkribiert, Gespeichert, Zusammenfassung fertig, Antwort wird gesucht …, Antwort gefunden, Wird noch fertiggestellt beim Beenden) werden angesagt. Umsetzung wie im Chatbot-Projekt. Falls es dort keine Lösung gibt: `QAccessibleAnnouncementEvent` (verfügbar ab Qt 6.8), sonst Statusleiste plus Accessibility-Event.
- Hintergrundmeldungen dürfen den Fokus nie verschieben und das Schreiben nicht unterbrechen.
- Nach jedem Ansichtswechsel steht der Fokus an einer vorhersehbaren Stelle (siehe jeweils oben).
- Keine Information nur über Farbe.
- Alle Dialoge lassen sich mit Escape schließen, Standardknöpfe sind sinnvoll gesetzt.

**Mehrzeiliges Textfeld „Was geschah“ (Recherche 23.09.2026):** Das Chatbot-Projekt (`Andere Projekte/Chatbot für Text`) hat sein `PlainEdit` bereits mit einer blinden Person am realen Screenreader getestet (siehe dessen `ACCESSIBILITY_TESTS.md`, Punkt 5h, und `DECISIONS.md`, Abschnitt „Frage- und Antwortfeld für Braillezeile“). Das Muster ist deshalb bewusst identisch übernommen: `QPlainTextEdit`, `setTabChangesFocus(True)`, Enter erzeugt einen echten Zeilenumbruch, kein eigener Override für die Pfeiltasten. Aus der dortigen Rückmeldung ist eine wichtige, aber nicht app-seitig behebbare Einschränkung bekannt: **Pfeiltasten-Navigation zeile­weise ist mit NVDA/Braillezeile nur zwischen echten Absätzen (`\n`) zuverlässig.** Innerhalb eines langen, nur automatisch umgebrochenen Absatzes (kein manueller Zeilenumbruch) kann der Pfeiltastendruck die neue Zeile nicht immer korrekt melden - das ist eine bekannte Eigenheit der Qt-Accessibility-Anbindung für Textfelder, keine Fehlfunktion dieser App. Für generierten Text (KI-Antworten) wird dem im Chatbot-Projekt mit „ein Satz je Zeile" begegnet; für frei getipptes Tagebuch-Prosa ist das nicht angemessen (würde die Schreibweise verfälschen) - hier hilft nur, beim Schreiben gelegentlich Enter für echte Absätze zu nutzen.

## 12. Projektstruktur (Vorschlag)

Diese Struktur ist ein Vorschlag. Die Struktur des Chatbot-Projekts hat Vorrang.

```
tagebuch/
  main.py
  config.toml
  requirements.txt
  README.md
  tagebuch/
    ui/
      hauptfenster.py
      einrichtung_dialog.py
      anmelde_dialog.py
      passwort_dialog.py
      uebersicht_ansicht.py
      editor_ansicht.py
      lese_ansicht.py
      such_dialog.py
      ansagen.py
    kern/
      krypto.py
      speicher.py
      modelle.py
      datum.py
      zeitplan.py
    ki/
      ollama_client.py
      zusammenfasser.py
      prompts.py
      warteschlange.py
    sprache/
      aufnahme.py
      umwandlung.py
  tests/
    test_krypto.py
    test_speicher.py
    test_datum.py
    test_zeitplan.py
```

`zeitplan.py` enthält die Logik, welche Zusammenfassungen fällig sind. Das heutige Datum wird als Parameter übergeben, damit sich Monats- und Jahreswechsel testen lassen.

## 13. Umsetzung in Phasen

Nach jeder Phase ist das Programm startbar und testbar. Nach jeder Phase kurz zusammenfassen, was fertig ist und wie der Nutzer es ausprobiert.

1. **Analyse** des Chatbot-Projekts, Zusammenfassung an den Nutzer (Abschnitt 2)
2. **Grundgerüst**: Projektstruktur, Konfiguration, Verschlüsselung, Datenbank, Einrichtung und Anmeldung, mit Tests
3. **Übersicht, Editor und Leseansicht** mit Tastaturbedienung, Datumsprüfung, Kontextmenü mit Löschen, Menü Rückschau
4. **Spracheingabe** mit faster-whisper
5. **Tages-Stichpunkte** mit Ollama und Hintergrund-Warteschlange
6. **Monats- und Jahresübersichten** inklusive Nachholen und Datumswechsel
7. **Suche**
8. **Passwort ändern**, Feinschliff, README mit Installationsanleitung für Windows

## 14. Annahmen und offene Punkte

Diese Punkte waren in den Wünschen des Nutzers nicht eindeutig. Die hier gewählte Lösung gilt, bis der Nutzer etwas anderes sagt.

- **A1:** In der Monats- und Jahresübersicht heißt der oberste Listeneintrag „Neue Monatsübersicht schreiben“ bzw. „Neue Jahresübersicht schreiben“. Er öffnet den Editor ohne Spracheingabe, das Feld „Monat“ bzw. „Jahr“ ist mit dem aktuellen Monat bzw. Jahr vorbelegt.
- **A2 (geändert am 23.09.2026):** Beim Bearbeiten vergangener **Tage** ist die Spracheingabe jetzt ebenfalls verfügbar, wie in Abschnitt 7.3. Bei Monats-/Jahresübersichten bleibt sie weiterhin ausgeblendet, da diese normalerweise per KI entstehen und manuelles Bearbeiten dort nur der Korrektur dient.
- **A3:** Nach dem Speichern geht es zurück zur Übersicht. Alternative: im Editor bleiben.
- **A4:** Die Stichpunkte des heutigen Tages werden nach jedem Speichern neu erzeugt, nicht erst am Tagesende.
- **A5:** Das Kontextmenü enthält zusätzlich „Zusammenfassung neu erstellen“. Das war nicht ausdrücklich gewünscht, ist aber nötig, um veraltete oder misslungene Zusammenfassungen zu erneuern.
- **A6:** Das Feld, das der Nutzer „Monatsauswahl“ genannt hat, ist das Datumsfeld und heißt in der Oberfläche „Datum“ (bzw. „Monat“ oder „Jahr“).
- **A7:** Wird ein Tageseintrag nachträglich geändert oder gelöscht, dessen Monat schon eine Übersicht hat, wird die Monatsübersicht nicht automatisch neu erstellt. Sie kann über das Kontextmenü neu erstellt werden.

## 15. Mögliche Erweiterungen (nicht Teil der ersten Version)

- Verschlüsselte Sicherungskopie auf einen USB-Stick oder in einen Cloud-Ordner exportieren
- Automatisches Sperren nach längerer Inaktivität
- Stimmungsverlauf als Diagramm
- Wochenübersicht
